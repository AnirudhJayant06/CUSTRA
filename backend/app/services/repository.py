"""Firestore-backed shared demo session records."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class SessionStore(Protocol):
    def create(self, token_hash: str, expires_at: datetime) -> None: ...
    def get(self, token_hash: str) -> dict | None: ...
    def revoke(self, token_hash: str) -> None: ...


class FirestoreSessionStore:
    def __init__(self, project_id: str, namespace: str = "shared"):
        self.project_id = project_id
        self.namespace = namespace
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            from google.cloud import firestore

            client = firestore.Client(project=self.project_id or None)
            self._collection = client.collection("custra_demo").document(self.namespace).collection("sessions")
        return self._collection

    def create(self, token_hash: str, expires_at: datetime) -> None:
        self.collection.document(token_hash).set({"expires_at": expires_at, "revoked": False})

    def get(self, token_hash: str) -> dict | None:
        snapshot = self.collection.document(token_hash).get()
        return snapshot.to_dict() if snapshot.exists else None

    def revoke(self, token_hash: str) -> None:
        self.collection.document(token_hash).set({"revoked": True}, merge=True)


class FirestoreVaultStore:
    """Records live under one explicit shared demo namespace."""

    def __init__(self, project_id: str, namespace: str = "shared"):
        self.project_id = project_id
        self.namespace = namespace
        self._root = None
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google.cloud import firestore
            self._client = firestore.Client(project=self.project_id or None)
        return self._client

    @property
    def root(self):
        if self._root is None:
            self._root = self.client.collection("custra_demo").document(self.namespace)
        return self._root

    def seed_demo_address(self, record: dict) -> None:
        from google.api_core.exceptions import Conflict

        try:
            self.root.collection("addresses").document(record["id"]).create(record)
        except Conflict:
            pass

    def get_profile(self) -> dict | None:
        snapshot = self.root.collection("account").document("profile").get()
        return snapshot.to_dict() if snapshot.exists else None

    def save_profile(self, record: dict) -> None:
        self.root.collection("account").document("profile").set(record)

    def list_addresses(self) -> list[dict]:
        return [snapshot.to_dict() for snapshot in self.root.collection("addresses").stream()]

    def get_address(self, id: str) -> dict | None:
        snapshot = self.root.collection("addresses").document(id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def save_address(self, record: dict) -> None:
        self.root.collection("addresses").document(record["id"]).set(record)

    def list_products(self) -> list[dict]:
        return [snapshot.to_dict() for snapshot in self.root.collection("products").stream()]

    def get_product(self, id: str) -> dict | None:
        snapshot = self.root.collection("products").document(id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def save_product(self, record: dict) -> None:
        from google.cloud import firestore

        ref = self.root.collection("products").document(record["id"])

        @firestore.transactional
        def save(transaction):
            previous = ref.get(transaction=transaction).to_dict()
            if previous and previous.get('deletedAt'):
                raise LookupError('Product not found')
            transaction.set(ref, record)

        save(self.client.transaction())


class FirestoreDocumentStore:
    def __init__(self, project_id: str, namespace: str = "shared"):
        self.vault = FirestoreVaultStore(project_id, namespace)

    @property
    def collection(self):
        return self.vault.root.collection("documents")

    def save(self, record: dict) -> None:
        self.collection.document(record["id"]).set(record)

    def get(self, document_id: str) -> dict | None:
        snapshot = self.collection.document(document_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def list_for_parent(self, parent_type: str, parent_id: str) -> list[dict]:
        query = self.collection.where("parentType", "==", parent_type).where("parentId", "==", parent_id)
        return [record for snapshot in query.stream() if (record := snapshot.to_dict()).get("status") == "ready"]


class FirestoreCaseStore:
    def __init__(self, project_id: str, namespace: str = "shared"):
        self.project_id = project_id
        self.namespace = namespace
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google.cloud import firestore

            self._client = firestore.Client(project=self.project_id or None)
        return self._client

    @property
    def root(self):
        return self.client.collection("custra_demo").document(self.namespace)

    def create_if_absent(self, key: str, digest: str, record: dict) -> dict:
        import hashlib
        from google.cloud import firestore
        from app.services.cases import IdempotencyConflict

        key_id = hashlib.sha256(key.encode()).hexdigest()
        key_ref = self.root.collection("creation_keys").document(key_id)
        case_ref = self.root.collection("cases").document(record["id"])

        @firestore.transactional
        def create(transaction):
            existing = key_ref.get(transaction=transaction)
            if existing.exists:
                saved = existing.to_dict()
                if saved["payloadHash"] != digest:
                    raise IdempotencyConflict("Request key already used for different details")
                return saved["response"]
            # Serialize creation against deletion using the same product read.
            product = self.root.collection('products').document(record['productId']).get(transaction=transaction).to_dict()
            if not product or product.get('deletedAt'):
                from app.services.leases import CaseConflict
                raise CaseConflict('Product was removed; choose another product')
            transaction.create(case_ref, record)
            transaction.create(key_ref, {"payloadHash": digest, "caseId": record["id"], "response": record})
            return record

        return create(self.client.transaction())

    def delete_product(self, product_id: str) -> dict:
        """Remove from the vault and close active cases in one transaction.

        Tombstones retain historical case/document references. Version changes
        reject stale agent/booking commits through the existing lease checks.
        """
        from datetime import timezone
        from google.cloud import firestore
        from google.cloud.firestore_v1.base_query import FieldFilter
        from app.services.leases import CaseConflict

        ref = self.root.collection('products').document(product_id)

        @firestore.transactional
        def remove(transaction):
            product = ref.get(transaction=transaction).to_dict()
            if not product:
                raise LookupError('Product not found')
            if product.get('deletedAt'):
                return {'id': product_id, 'deleted': True, 'closedComplaints': 0}
            query = self.root.collection('cases').where(filter=FieldFilter('productId', '==', product_id))
            cases = [snapshot for snapshot in query.stream(transaction=transaction)
                     if snapshot.to_dict()['status'] != 'CLOSED']
            # Two writes per active case plus one product tombstone.
            if len(cases) > 200:
                raise CaseConflict('Too many active complaints to delete this product at once')
            now = datetime.now(timezone.utc).isoformat()
            transaction.update(ref, {'deletedAt': now, 'updatedAt': now})
            for snapshot in cases:
                case = snapshot.to_dict()
                sequence = case.get('eventSequence', 0) + 1
                transaction.update(snapshot.reference, {
                    'status': 'CLOSED', 'closureReason': 'product_deleted',
                    'closedAt': now, 'updatedAt': now,
                    'currentVersion': case['currentVersion'] + 1, 'eventSequence': sequence,
                    'pendingSlotId': None, 'error': None, 'recoveryPhase': None,
                })
                event_id = f"{case['id']}-product-deletion"
                transaction.set(snapshot.reference.collection('events').document(event_id), {
                    'eventId': event_id, 'sequence': sequence, 'role': 'user',
                    'displayText': 'Complaint closed because the product was deleted.',
                    'simulated': False, 'createdAt': now,
                })
            return {'id': product_id, 'deleted': True, 'closedComplaints': len(cases)}

        return remove(self.client.transaction())

    def replay_creation(self, key: str, digest: str) -> dict | None:
        import hashlib
        from app.services.cases import IdempotencyConflict

        key_id = hashlib.sha256(key.encode()).hexdigest()
        snapshot = self.root.collection("creation_keys").document(key_id).get()
        if not snapshot.exists:
            return None
        saved = snapshot.to_dict()
        if saved["payloadHash"] != digest:
            raise IdempotencyConflict("Request key already used for different details")
        return saved["response"]

    def get(self, case_id: str) -> dict | None:
        snapshot = self.root.collection("cases").document(case_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def list(self, product_id: str | None = None) -> list[dict]:
        query = self.root.collection("cases")
        if product_id:
            from google.cloud.firestore_v1.base_query import FieldFilter

            query = query.where(filter=FieldFilter("productId", "==", product_id))
        return sorted([snapshot.to_dict() for snapshot in query.stream()],
                      key=lambda record: record["createdAt"], reverse=True)

    def acquire_advance(self, case_id: str, expected_version: int) -> dict:
        from datetime import datetime, timezone
        from google.cloud import firestore
        from app.services.leases import acquire_lease

        case_ref = self.root.collection("cases").document(case_id)

        @firestore.transactional
        def acquire(transaction):
            snapshot = case_ref.get(transaction=transaction)
            if not snapshot.exists:
                raise LookupError("Complaint not found")
            case = snapshot.to_dict()
            operation_id = f"{case_id}-advance-{case.get('stepIndex', 0)}"
            operation_ref = self.root.collection("operations").document(operation_id)
            previous = operation_ref.get(transaction=transaction)
            operation = previous.to_dict() if previous.exists else {"operationId": operation_id}
            lease = acquire_lease(case, operation, expected_version, datetime.now(timezone.utc))
            transaction.set(operation_ref, lease)
            return {"case": case, "operation": lease}

        return acquire(self.client.transaction())

    def _mutate_owned_operation(self, lease: dict, apply):
        from datetime import datetime, timezone
        from google.cloud import firestore
        from app.services.leases import check_lease

        case_ref = self.root.collection("cases").document(lease["case"]["id"])
        operation_ref = self.root.collection("operations").document(lease["operation"]["operationId"])

        @firestore.transactional
        def mutate(transaction):
            case = case_ref.get(transaction=transaction).to_dict()
            operation = operation_ref.get(transaction=transaction).to_dict()
            check_lease(case, operation, lease["operation"], datetime.now(timezone.utc))
            return apply(transaction, case_ref, operation_ref, case, operation)

        return mutate(self.client.transaction())

    def save_answer(self, lease: dict, answer: dict) -> None:
        def apply(transaction, case_ref, operation_ref, case, operation):
            transaction.update(operation_ref, {"savedAnswer": answer})

        self._mutate_owned_operation(lease, apply)

    def commit_advance(self, lease: dict, changes: dict, events: list[dict]) -> dict:
        from datetime import datetime, timezone

        def apply(transaction, case_ref, operation_ref, case, operation):
            updated = {**case, **changes, "currentVersion": case["currentVersion"] + 1,
                       "stepIndex": case.get("stepIndex", 0) + 1,
                       "updatedAt": datetime.now(timezone.utc).isoformat()}
            transaction.set(case_ref, updated)
            for event in events:
                transaction.set(case_ref.collection("events").document(event["eventId"]),
                                {**event, "createdAt": updated["updatedAt"]})
            transaction.update(operation_ref, {"leaseToken": None, "completed": True})
            return updated

        return self._mutate_owned_operation(lease, apply)

    def fail_advance(self, lease: dict) -> dict:
        def apply(transaction, case_ref, operation_ref, case, operation):
            updated = {**case, "status": "ERROR", "recoveryPhase": "advance",
                       "currentVersion": case["currentVersion"] + 1,
                       "error": {"message": "The agent step could not finish. Retry to resume." if operation.get("attemptCount", 0) < 3 else "Retry limit reached. Restart registration after checking its outcome.", "retryable": operation.get("attemptCount", 0) < 3}}
            transaction.set(case_ref, updated)
            transaction.update(operation_ref, {"leaseToken": None})
            return updated

        return self._mutate_owned_operation(lease, apply)

    def events(self, case_id: str, after: int = 0) -> list[dict]:
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.root.collection("cases").document(case_id).collection("events")
        return [snapshot.to_dict() for snapshot in query.where(filter=FieldFilter("sequence", ">", after))
                .order_by("sequence").stream()]

    def acquire_booking(self, case_id: str, expected_version: int, slot_id: str, key_hash: str) -> dict:
        from datetime import datetime, timezone
        from google.cloud import firestore
        from app.services.leases import acquire_lease, CaseConflict

        case_ref = self.root.collection("cases").document(case_id)
        operation_ref = self.root.collection("operations").document(f"{case_id}-book")

        @firestore.transactional
        def acquire(transaction):
            case = case_ref.get(transaction=transaction).to_dict()
            if not case:
                raise LookupError("Complaint not found")
            saved = operation_ref.get(transaction=transaction)
            operation = saved.to_dict() if saved.exists else {
                "operationId": f"{case_id}-book", "slotId": slot_id, "keyHash": key_hash}
            if operation["slotId"] != slot_id:
                raise CaseConflict("Recover the pending booking before selecting a different slot")
            lease = acquire_lease(case, operation, expected_version, datetime.now(timezone.utc), "book")
            transaction.set(operation_ref, lease)
            transaction.update(case_ref, {"pendingSlotId": slot_id})
            return {"case": {**case, "pendingSlotId": slot_id}, "operation": lease}

        return acquire(self.client.transaction())

    def commit_booking(self, lease: dict, appointment: dict) -> dict:
        from datetime import datetime, timezone

        def apply(transaction, case_ref, operation_ref, case, operation):
            updated = {**case, "status": "BOOKED", "appointment": appointment,
                       "bookingKeyHash": operation["keyHash"], "pendingSlotId": None,
                       "recoveryPhase": None, "error": None,
                       "currentVersion": case["currentVersion"] + 1,
                       "eventSequence": case.get("eventSequence", 0) + 1}
            transaction.set(case_ref, updated)
            transaction.update(operation_ref, {"leaseToken": None, "completed": True})
            transaction.set(case_ref.collection("events").document(f"{operation['operationId']}-confirmed"), {
                "eventId": f"{operation['operationId']}-confirmed", "sequence": updated["eventSequence"],
                "role": "business", "simulated": True, "displayText": "Simulated appointment confirmed.",
                "createdAt": datetime.now(timezone.utc).isoformat(),
            })
            return updated

        return self._mutate_owned_operation(lease, apply)

    def fail_booking(self, lease: dict) -> dict:
        def apply(transaction, case_ref, operation_ref, case, operation):
            updated = {**case, "status": "ERROR", "recoveryPhase": "book",
                       "pendingSlotId": operation["slotId"], "currentVersion": case["currentVersion"] + 1,
                       "error": {"message": "Booking confirmation is pending. Retry the same selected slot." if operation.get("attemptCount", 0) < 3 else "Booking outcome is uncertain. Do not create another booking; contact business support.", "retryable": operation.get("attemptCount", 0) < 3}}
            transaction.set(case_ref, updated)
            transaction.update(operation_ref, {"leaseToken": None})
            return updated

        return self._mutate_owned_operation(lease, apply)

    def close_case(self, case_id: str) -> dict:
        from datetime import datetime, timezone
        from google.cloud import firestore
        from app.services.leases import CaseConflict

        ref = self.root.collection("cases").document(case_id)

        @firestore.transactional
        def close(transaction):
            case = ref.get(transaction=transaction).to_dict()
            if not case:
                raise LookupError("Complaint not found")
            if case["status"] == "CLOSED":
                return case
            if case["status"] != "BOOKED":
                raise CaseConflict("Only a booked case can be confirmed resolved")
            updated = {**case, "status": "CLOSED", "currentVersion": case["currentVersion"] + 1,
                       "eventSequence": case.get("eventSequence", 0) + 1,
                       "resolvedAt": datetime.now(timezone.utc).isoformat()}
            transaction.set(ref, updated)
            transaction.set(ref.collection("events").document(f"{case_id}-user-closure"), {
                "eventId": f"{case_id}-user-closure", "sequence": updated["eventSequence"],
                "role": "user", "simulated": False, "displayText": "Issue confirmed resolved by the user.",
                "createdAt": updated["resolvedAt"],
            })
            return updated

        return close(self.client.transaction())

    def interact(self, case_id, expected_version, changes, text=None):
        """Versioned customer action; invalidates stale drafts, never an external send."""
        from datetime import timezone
        from google.cloud import firestore
        from app.services.leases import CaseConflict
        ref = self.root.collection('cases').document(case_id)
        @firestore.transactional
        def apply(transaction):
            case = ref.get(transaction=transaction).to_dict()
            if not case:
                raise LookupError('Complaint not found')
            if case['currentVersion'] != expected_version or case['status'] in {'CLOSED', 'BOOKED'}:
                raise CaseConflict('Complaint changed; reload before continuing')
            op_ref = self.root.collection('operations').document(f"{case_id}-advance-{case.get('stepIndex', 0)}")
            op = op_ref.get(transaction=transaction).to_dict()
            updated = {**case, **changes, 'currentVersion': expected_version+1,
                       'updatedAt': datetime.now(timezone.utc).isoformat()}
            if text:
                updated['eventSequence'] = case.get('eventSequence', 0)+1
                transaction.set(ref.collection('events').document(f'{case_id}-input-{expected_version}'), {
                    'eventId': f'{case_id}-input-{expected_version}', 'sequence': updated['eventSequence'],
                    'role': 'user', 'displayText': text, 'simulated': False, 'createdAt': updated['updatedAt']})
            if op:
                if op.get('sendStarted') and text:
                    updated['queuedCorrection'] = text
                elif not op.get('sendStarted'):
                    transaction.update(op_ref, {'savedAnswer': None, 'leaseToken': None})
            transaction.set(ref, updated)
            return updated
        return apply(self.client.transaction())

    def mark_send(self, lease):
        def apply(transaction, case_ref, operation_ref, case, operation):
            transaction.update(operation_ref, {'sendStarted': True})
        self._mutate_owned_operation(lease, apply)

    def save_external_result(self, operation_id, response):
        self.root.collection('operations').document(operation_id).update({'externalResult': response})
