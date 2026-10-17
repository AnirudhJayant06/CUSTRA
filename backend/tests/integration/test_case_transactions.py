"""Emulator-only transaction checks. Never connects to production Firestore."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from app.services.repository import FirestoreCaseStore
from app.services.leases import CaseConflict


def emulator_store():
    host = os.getenv("FIRESTORE_EMULATOR_HOST", "")
    if not host:
        pytest.skip("Firestore emulator is not configured")
    if not host.startswith(("127.0.0.1:", "localhost:", "[::1]:")):
        pytest.fail("Transaction tests require a loopback Firestore emulator")
    return FirestoreCaseStore("demo-custra-tests", namespace=f"test-{uuid.uuid4().hex}")


def test_racing_duplicate_creations_produce_one_case():
    store = emulator_store()
    store.root.collection('products').document('fictional-product').set({'id': 'fictional-product'})
    records = [{"id": uuid.uuid4().hex, "createdAt": "2026-10-16T00:00:00+00:00", "productId": "fictional-product"}
               for _ in range(2)]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(store.create_if_absent, "fictional-stable-key", "same-payload", record)
                       for record in records]
            results = [future.result(timeout=15) for future in futures]
        assert results[0]["id"] == results[1]["id"]
        assert len(store.list()) == 1
    finally:
        for collection in ("cases", "creation_keys", "products"):
            for snapshot in store.root.collection(collection).stream():
                snapshot.reference.delete()


def cleanup(store):
    for case in store.root.collection("cases").stream():
        for event in case.reference.collection("events").stream(): event.reference.delete()
        case.reference.delete()
    for collection in ("operations", "creation_keys"):
        for row in store.root.collection(collection).stream(): row.reference.delete()


def test_expired_lease_stale_commit_and_cached_answer_survive_recreation():
    store = emulator_store()
    case = {"id": "fictional-case", "currentVersion": 0, "status": "PROCESSING", "stepIndex": 0,
            "eventSequence": 0, "createdAt": datetime.now(timezone.utc).isoformat()}
    store.root.collection("cases").document(case["id"]).set(case)
    try:
        def acquire():
            try: return store.acquire_advance(case["id"], 0)
            except CaseConflict: return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: acquire(), range(2)))
        assert sum(result is not None for result in results) == 1
        stale = next(result for result in results if result)
        op_ref = store.root.collection("operations").document(stale["operation"]["operationId"])
        op_ref.update({"expiresAt": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()})
        renewed = store.acquire_advance(case["id"], 0)
        with pytest.raises(CaseConflict): store.commit_advance(stale, {"status": "PROCESSING"}, [])
        store.save_answer(renewed, {"text": "Fictional", "field_refs": ["product.model"]})
        failed = store.fail_advance(renewed)
        recreated = FirestoreCaseStore("demo-custra-tests", namespace=store.namespace)
        retry = recreated.acquire_advance(case["id"], failed["currentVersion"])
        assert retry["operation"]["operationId"] == renewed["operation"]["operationId"]
        assert retry["operation"]["savedAnswer"]["text"] == "Fictional"
        committed = recreated.commit_advance(retry, {"status": "PROCESSING", "eventSequence": 1}, [{
            "eventId": "fictional-event", "sequence": 1, "role": "business", "displayText": "Fictional question", "simulated": True}])
        assert committed["currentVersion"] == 2
        assert len(recreated.events(case["id"])) == 1
        with pytest.raises(CaseConflict): recreated.commit_advance(retry, {"status": "PROCESSING"}, [])
    finally:
        cleanup(store)


def test_booking_and_user_closure_survive_store_recreation():
    store = emulator_store()
    case = {"id": "fictional-case", "currentVersion": 0, "status": "AWAITING_APPOINTMENT",
            "eventSequence": 9, "createdAt": datetime.now(timezone.utc).isoformat()}
    store.root.collection("cases").document(case["id"]).set(case)
    try:
        lease = store.acquire_booking(case["id"], 0, "slot-1", "fictional-key-hash")
        failed = store.fail_booking(lease)
        recreated = FirestoreCaseStore("demo-custra-tests", namespace=store.namespace)
        retry = recreated.acquire_booking(case["id"], failed["currentVersion"], "slot-1", "new-fictional-key-hash")
        assert retry["operation"]["operationId"] == lease["operation"]["operationId"]
        appointment = {"slotId": "slot-1", "bookingReference": "DEMO-BOOK-1"}
        recreated.commit_booking(retry, appointment)
        assert store.get(case["id"])["status"] == "BOOKED"
        assert len(store.events(case["id"])) == 1
        recreated.close_case(case["id"])
        recreated.close_case(case["id"])
        assert store.get(case["id"])["status"] == "CLOSED"
        assert len(store.events(case["id"])) == 2
    finally:
        cleanup(store)


def test_simulator_replay_uses_firestore_after_recreation():
    # Reuse the guarded emulator binding, with a separate simulator test namespace.
    binding = emulator_store()
    from executor import BusinessService
    from store import FirestoreReplayStore

    persistent = FirestoreReplayStore("demo-custra-tests", namespace=binding.namespace)
    request = {"schema_version": 1, "case_id": "fictional-case", "operation_id": "fictional-start",
               "scenario_id": "basic", "action": "start", "stage": "new", "data": {}}
    try:
        first = BusinessService(persistent).exchange(request, "context-1")
        second_store = FirestoreReplayStore("demo-custra-tests", namespace=binding.namespace)
        assert BusinessService(second_store).exchange(request, "different-transport-context") == first
    finally:
        for collection in ("cases", "operations"):
            for row in persistent.root.collection(collection).stream(): row.reference.delete()


def test_case_and_a2a_simulator_recover_in_fresh_processes():
    import json
    import subprocess
    import sys
    from pathlib import Path
    from store import FirestoreReplayStore

    binding = emulator_store()
    root = Path(__file__).resolve().parents[3]
    environment = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(root / 'backend'), str(root / 'manufacturer-agent/app')])}
    def run(phase):
        result = subprocess.run([sys.executable, str(root / 'backend/tests/support/restart_flow.py'), binding.namespace, phase],
                                env=environment, capture_output=True, text=True, timeout=40, check=True)
        return json.loads(result.stdout)
    try:
        first = run('start')
        resumed = run('resume')
        assert first['status'] == 'PROCESSING' and len(first['events']) == 3
        assert resumed['status'] == 'BOOKED' and len(resumed['events']) == 10
        assert resumed['id'] == first['id'] and resumed['context'] == first['context']
        assert resumed['events'][:3] == first['events']
        assert len(set(resumed['events'])) == 10
    finally:
        cleanup(binding)
        for collection in ('account', 'addresses', 'products'):
            for row in binding.root.collection(collection).stream(): row.reference.delete()
        simulator = FirestoreReplayStore('demo-custra-tests', binding.namespace)
        for collection in ('cases', 'operations'):
            for row in simulator.root.collection(collection).stream(): row.reference.delete()
