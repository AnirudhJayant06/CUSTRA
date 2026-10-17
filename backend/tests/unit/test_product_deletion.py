"""Deletion contract using an in-memory Firestore transaction boundary."""
import copy
from datetime import datetime, timezone

import pytest

from app.services.repository import FirestoreCaseStore, FirestoreVaultStore
from app.services.vault import VaultService
from app.services.leases import CaseConflict, check_lease
from backend.tests.unit.test_vault import FakeVaultStore


class Snapshot:
    def __init__(self, ref): self.reference = ref; self.exists = ref.path in ref.rows
    def to_dict(self): return copy.deepcopy(self.reference.rows.get(self.reference.path))


class Ref:
    def __init__(self, rows, path='root', condition=None): self.rows = rows; self.path = path; self.condition = condition
    def collection(self, name): return Ref(self.rows, self.path + '/' + name)
    def document(self, name): return Ref(self.rows, self.path + '/' + name)
    def get(self, transaction=None): return Snapshot(self)
    def where(self, *, filter): return Ref(self.rows, self.path, (filter.field_path, filter.op_string, filter.value))
    def order_by(self, field): return self
    def stream(self, transaction=None):
        for path, row in list(self.rows.items()):
            matches = not self.condition or (row.get(self.condition[0]) == self.condition[2] if self.condition[1] == '==' else row.get(self.condition[0], 0) > self.condition[2])
            if path.rsplit('/', 1)[0] == self.path and matches:
                yield Snapshot(Ref(self.rows, path))


class Client:
    def __init__(self): self.rows = {}
    def collection(self, name): return Ref(self.rows, name)
    def transaction(self): return self
    def set(self, ref, row): self.rows[ref.path] = copy.deepcopy(row)
    def create(self, ref, row): assert ref.path not in self.rows; self.set(ref, row)
    def update(self, ref, row): self.rows[ref.path].update(copy.deepcopy(row))


def store(monkeypatch):
    monkeypatch.setattr('google.cloud.firestore.transactional', lambda fn: fn)
    result = FirestoreCaseStore('demo-custra-tests')
    result._client = Client()
    result.client.set(result.root.collection('products').document('phone'), {'id': 'phone'})
    return result


def test_deleted_products_are_hidden_from_vault_and_cannot_be_edited():
    rows = FakeVaultStore()
    rows.products = {'phone': {'id': 'phone', 'deletedAt': '2026-10-17'}, 'tv': {'id': 'tv'}}
    vault = VaultService(rows)
    assert vault.list_products() == [{'id': 'tv'}]
    with pytest.raises(LookupError): vault.get_product('phone')
    with pytest.raises(LookupError): vault.update_product('phone', {'nickname': 'Revive'})


def test_delete_closes_all_active_cases_preserves_history_and_invalidates_worker(monkeypatch):
    repository = store(monkeypatch)
    for id, product, status in [('working', 'phone', 'PROCESSING'), ('booked', 'phone', 'BOOKED'), ('resolved', 'phone', 'CLOSED'), ('other', 'tv', 'PROCESSING')]:
        repository.client.set(repository.root.collection('cases').document(id), {'id': id, 'productId': product, 'status': status, 'currentVersion': 2, 'eventSequence': 9, 'factsSnapshot': {'product': {'displayName': 'Old phone'}}})
    result = repository.delete_product('phone')
    assert result['closedComplaints'] == 2
    assert repository.root.collection('products').document('phone').get().to_dict()['deletedAt']
    for id in ('working', 'booked'):
        row = repository.get(id)
        assert row['status'] == 'CLOSED' and row['closureReason'] == 'product_deleted'
        assert row['currentVersion'] == 3 and 'resolvedAt' not in row
        assert row['factsSnapshot']['product']['displayName'] == 'Old phone'
        assert len(repository.events(id)) == 1
    assert repository.get('resolved')['currentVersion'] == 2
    assert repository.get('other')['status'] == 'PROCESSING'
    operation = {'leaseToken': 'old', 'caseVersion': 2, 'expiresAt': '2099-01-01T00:00:00+00:00'}
    with pytest.raises(CaseConflict): check_lease(repository.get('working'), operation, operation, datetime.now(timezone.utc))
    assert repository.delete_product('phone')['closedComplaints'] == 0
    assert len(repository.events('working')) == 1


def test_new_case_cannot_race_a_deleted_product(monkeypatch):
    repository = store(monkeypatch)
    repository.delete_product('phone')
    with pytest.raises(CaseConflict):
        repository.create_if_absent('new-case-request-key', 'digest', {'id': 'late', 'productId': 'phone'})
    assert repository.get('late') is None


def test_stale_product_edit_cannot_restore_a_deleted_product(monkeypatch):
    repository = store(monkeypatch)
    repository.delete_product('phone')
    vault_store = FirestoreVaultStore('demo-custra-tests')
    vault_store._client = repository.client
    with pytest.raises(LookupError): vault_store.save_product({'id': 'phone', 'nickname': 'Restore'})
    assert repository.root.collection('products').document('phone').get().to_dict()['deletedAt']
