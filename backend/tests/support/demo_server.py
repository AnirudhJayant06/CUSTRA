"""Local-only browser fixture. All persistence/model boundaries are injected fakes.

This module is never imported by app.main or the production Docker image entrypoint.
"""

import asyncio
import copy
import json
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.agents.consumer import answer_text
from app.config import Settings
from app.main import create_app
from app.models.exchange import ValidatedAnswer
from app.services.a2a_gateway import A2AGateway
from app.services.auth import hash_password
from app.services.cases import IdempotencyConflict
from app.services.leases import CaseConflict, acquire_lease, check_lease
from executor import BusinessService
from main import create_app as create_business_app


class Sessions:
    def __init__(self): self.rows = {}
    def create(self, key, expires_at): self.rows[key] = {"expires_at": expires_at, "revoked": False}
    def get(self, key): return self.rows.get(key)
    def revoke(self, key):
        if key in self.rows: self.rows[key]["revoked"] = True


class Vault:
    def __init__(self): self.profile = None; self.addresses = {}; self.products = {}
    def seed_demo_address(self, row): self.addresses.setdefault(row["id"], copy.deepcopy(row))
    def get_profile(self): return copy.deepcopy(self.profile)
    def save_profile(self, row): self.profile = copy.deepcopy(row)
    def list_addresses(self): return copy.deepcopy(list(self.addresses.values()))
    def get_address(self, key): return copy.deepcopy(self.addresses.get(key))
    def save_address(self, row): self.addresses[row["id"]] = copy.deepcopy(row)
    def list_products(self): return copy.deepcopy(list(self.products.values()))
    def get_product(self, key): return copy.deepcopy(self.products.get(key))
    def save_product(self, row): self.products[row["id"]] = copy.deepcopy(row)


class Documents:
    def __init__(self): self.rows = {}
    def save(self, row): self.rows[row["id"]] = copy.deepcopy(row)
    def get(self, key): return copy.deepcopy(self.rows.get(key))
    def list_for_parent(self, kind, key):
        return [copy.deepcopy(row) for row in self.rows.values()
                if row["parentType"] == kind and row["parentId"] == key and row["status"] == "ready"]


class Bucket:
    def __init__(self): self.objects = {}
    def blob(self, key):
        import io
        bucket = self
        class Blob:
            def upload_from_file(self, stream, content_type): bucket.objects[key] = stream.read()
            def open(self, mode): return io.BytesIO(bucket.objects[key])
            def delete(self): bucket.objects.pop(key, None)
        return Blob()


class Cases:
    def __init__(self): self.rows = {}; self.keys = {}; self.operations = {}; self.messages = {}; self.lock = threading.RLock()
    def delete_product(self, key):
        with self.lock:
            product = self.vault.get_product(key)
            if not product: raise LookupError('Product not found')
            if product.get('deletedAt'): return {'id': key, 'deleted': True, 'closedComplaints': 0}
            now = datetime.now(timezone.utc).isoformat()
            product.update(deletedAt=now, updatedAt=now); self.vault.save_product(product)
            count = 0
            for row in self.rows.values():
                if row['productId'] != key or row['status'] == 'CLOSED': continue
                row.update(status='CLOSED', closureReason='product_deleted', closedAt=now, pendingSlotId=None, error=None, recoveryPhase=None)
                row['currentVersion'] += 1; row['eventSequence'] += 1; count += 1
                self.messages.setdefault(row['id'], []).append({'eventId': f"{row['id']}-product-deletion", 'sequence': row['eventSequence'], 'role': 'user', 'simulated': False, 'createdAt': now, 'displayText': 'Complaint closed because the product was deleted.'})
            return {'id': key, 'deleted': True, 'closedComplaints': count}
    def replay_creation(self, key, digest):
        with self.lock:
            if key not in self.keys: return None
            saved_digest, case_id = self.keys[key]
            if saved_digest != digest: raise IdempotencyConflict
            return copy.deepcopy(self.rows[case_id])
    def create_if_absent(self, key, digest, row):
        with self.lock:
            previous = self.replay_creation(key, digest)
            if previous: return previous
            self.keys[key] = (digest, row["id"])
            self.rows[row["id"]] = copy.deepcopy(row)
            return copy.deepcopy(row)
    def get(self, key):
        with self.lock: return copy.deepcopy(self.rows.get(key))
    def list(self, product_id=None):
        with self.lock: return [copy.deepcopy(row) for row in self.rows.values() if not product_id or row["productId"] == product_id]
    def events(self, key, after=0):
        with self.lock: return [copy.deepcopy(event) for event in self.messages.get(key, []) if event["sequence"] > after]
    def acquire(self, key, version, phase, slot_id=None, key_hash=None):
        with self.lock:
            case = self.rows[key]
            operation_id = f"{key}-advance-{case['stepIndex']}" if phase == "advance" else f"{key}-book"
            previous = self.operations.get(operation_id, {"operationId": operation_id})
            if phase == "book":
                if previous.get("slotId", slot_id) != slot_id: raise CaseConflict("Pending slot differs")
                previous.update(slotId=slot_id, keyHash=previous.get("keyHash", key_hash))
                case["pendingSlotId"] = slot_id
            operation = acquire_lease(case, previous, version, datetime.now(timezone.utc), phase)
            self.operations[operation_id] = operation
            return {"case": copy.deepcopy(case), "operation": copy.deepcopy(operation)}
    def acquire_advance(self, key, version): return self.acquire(key, version, "advance")
    def acquire_booking(self, key, version, slot_id, key_hash): return self.acquire(key, version, "book", slot_id, key_hash)
    def owned(self, lease):
        case = self.rows[lease["case"]["id"]]
        operation = self.operations[lease["operation"]["operationId"]]
        check_lease(case, operation, lease["operation"], datetime.now(timezone.utc))
        return case, operation
    def save_answer(self, lease, answer):
        with self.lock:
            _, operation = self.owned(lease)
            operation["savedAnswer"] = copy.deepcopy(answer)
    def save_preparation(self, lease, preparation):
        with self.lock:
            _, operation = self.owned(lease)
            operation['preparation'] = copy.deepcopy(preparation)
    def commit_advance(self, lease, changes, events):
        with self.lock:
            case, operation = self.owned(lease)
            case.update(copy.deepcopy(changes)); case["currentVersion"] += 1; case["stepIndex"] += 1
            self.messages.setdefault(case["id"], []).extend(copy.deepcopy(events))
            operation["leaseToken"] = None
            return copy.deepcopy(case)
    def fail(self, lease, phase):
        with self.lock:
            case, operation = self.owned(lease)
            case.update(status="ERROR", recoveryPhase=phase, error={"message": "Test step failed. Retry to resume." if operation.get("attemptCount", 0) < 3 else "Retry limit reached. Restart registration.", "retryable": operation.get("attemptCount", 0) < 3})
            case["currentVersion"] += 1; operation["leaseToken"] = None
            if phase == "book": case["pendingSlotId"] = operation["slotId"]
            return copy.deepcopy(case)
    def fail_advance(self, lease): return self.fail(lease, "advance")
    def fail_booking(self, lease): return self.fail(lease, "book")
    def commit_booking(self, lease, appointment):
        with self.lock:
            case, operation = self.owned(lease)
            case.update(status="BOOKED", appointment=copy.deepcopy(appointment), pendingSlotId=None, recoveryPhase=None, error=None)
            case["currentVersion"] += 1; operation["leaseToken"] = None
            return copy.deepcopy(case)
    def close_case(self, key):
        with self.lock:
            case = self.rows[key]
            if case["status"] not in {"BOOKED", "CLOSED"}: raise CaseConflict
            case["status"] = "CLOSED"; case["currentVersion"] += 1
            return copy.deepcopy(case)


    def interact(self, key, version, changes, text=None):
        with self.lock:
            case = self.rows[key]
            if case['currentVersion'] != version or case['status'] in {'BOOKED', 'CLOSED'}:
                raise CaseConflict('Complaint changed')
            case.update(copy.deepcopy(changes)); case['currentVersion'] += 1
            if text:
                case['eventSequence'] += 1
                self.messages.setdefault(key, []).append({'eventId': f'{key}-input-{version}', 'sequence': case['eventSequence'],
                    'role': 'user', 'displayText': text, 'simulated': False})
            op = self.operations.get(f"{key}-advance-{case['stepIndex']}")
            if op and not op.get('sendStarted'):
                op.update(savedAnswer=None, leaseToken=None)
            return copy.deepcopy(case)
    def mark_send(self, lease):
        with self.lock:
            _, op = self.owned(lease); op['sendStarted'] = True
    def save_external_result(self, operation_id, result):
        with self.lock: self.operations[operation_id]['externalResult'] = copy.deepcopy(result)


class Replay:
    def __init__(self): self.operations = {}; self.cases = {}; self.lock = threading.Lock()
    def transact(self, key, digest, case_id, generate):
        with self.lock:
            if key in self.operations:
                previous_digest, response = self.operations[key]
                if digest != previous_digest: raise ValueError("Changed payload")
                return copy.deepcopy(response)
            response, state = generate(copy.deepcopy(self.cases.get(case_id, {})))
            self.cases[case_id] = state
            self.operations[key] = (digest, copy.deepcopy(response))
            return copy.deepcopy(response)


controls = {"fail_model_once": False, "model_calls": 0}


class Consumer:
    async def answer(self, question, facts, transcript):
        controls["model_calls"] += 1
        await asyncio.sleep(0.15)
        if controls["fail_model_once"]:
            controls["fail_model_once"] = False
            raise ValueError("Injected test-only model failure")
        return ValidatedAnswer(text=answer_text(question.requested_fields, facts), field_refs=question.requested_fields)


auth_path = Path(os.getenv("CUSTRA_E2E_AUTH_PATH", "/tmp/custra-e2e-credentials.json"))
credentials = {"username": "fictional-reviewer", "password": secrets.token_urlsafe(24)}
auth_path.write_text(json.dumps(credentials))
auth_path.chmod(0o600)
app = create_app(settings=Settings(
    demo_username=credentials["username"], password_hash=hash_password(credentials["password"]),
    secure_cookies=False, app_origin=os.getenv("CUSTRA_APP_ORIGIN", "http://127.0.0.1:5178")),
    session_store=Sessions(), vault_store=Vault(), file_store=Documents(), file_bucket=Bucket(), case_store=Cases())
app.state.cases.store.vault = app.state.vault.store
replay = Replay()
business_app = create_business_app("http://business.test", store=replay)
transport_client = httpx.AsyncClient(transport=httpx.ASGITransport(app=business_app), base_url="http://business.test", timeout=8)
app.state.cases.gateway = A2AGateway("http://business.test", transport_client)
app.state.cases.consumer = Consumer()


@app.post("/test/reset")
def reset():
    app.state.session_store = Sessions(); app.state.vault.store = Vault(); app.state.cases.store = Cases()
    app.state.cases.store.vault = app.state.vault.store
    app.state.files.store = Documents(); app.state.files.bucket = Bucket()
    app.state.knowledge = None; app.state.cases.conversation = None
    replay.operations.clear(); replay.cases.clear()
    controls.update(fail_model_once=False, model_calls=0)
    return {"reset": True}


@app.post("/test/fail-model")
def fail_model():
    controls["fail_model_once"] = True
    return {"configured": True}


@app.post("/test/expire-session")
def expire_session():
    for row in app.state.session_store.rows.values(): row["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    return {"expired": True}


@app.get("/test/state")
def state():
    return {"cases": app.state.cases.store.list(), "modelCalls": controls["model_calls"], "preparationAttempts": {key: op.get("preparation", {}).get("attempts", {}) for key, op in app.state.cases.store.operations.items()}}


@app.post('/test/natural')
def enable_natural(request_document: bool = False):
    from knowledge_fixtures import Records, FixtureModel
    from app.services.knowledge import KnowledgeService
    from app.services.conversation import ConversationService
    model = FixtureModel(request_document=request_document)
    app.state.knowledge = KnowledgeService(Records(), model, app.state.files, app.state.vault)
    async def exchange(request):
        if request_document and request.action == 'start':
            request = request.model_copy(update={'data': {'request_document': True}})
        return await app.state.cases._exchange(request)
    app.state.cases.conversation = ConversationService(app.state.cases.store, app.state.knowledge, model, exchange)
    return {'enabled': True}


@app.post('/test/fail-natural')
def fail_natural(count: int = 3):
    app.state.knowledge.model.fail_answers = min(max(count, 0), 3)
    return {'configured': True}


@app.post('/test/await-detail')
def historical_handoff(case_id: str):
    store = app.state.cases.store
    with store.lock:
        case = store.rows[case_id]
        assert case['businessStage'] == 'purchase'
        case.update(status='AWAITING_USER', pendingUserRequest={'kind': 'fact', 'prompt': 'Purchase date', 'fields': ['product.purchaseDate']})
        case['currentVersion'] += 1
    return {'restored': True}
