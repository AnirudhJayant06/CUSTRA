import pytest
import httpx
from datetime import datetime, timedelta, timezone

from app.services.cases import CaseService, CaseValidationError, IdempotencyConflict
from app.services.vault import VaultService
from app.main import create_app
from app.config import Settings
from app.services.auth import token_digest
from app.models.complaint import ComplaintInput


class FakeVault:
    def __init__(self):
        self.profile = {"name": "Fictional User", "phone": "9999999999", "email": "fictional@example.test"}
        self.product = {"id": "product-1", "categoryId": "smartphone", "brandId": "samsung",
                        "displayName": "Example Phone"}
        self.address = {"id": "address-1", "label": "Home", "line1": "1 Fiction Lane",
                        "city": "Pune", "region": "Maharashtra", "postalCode": "411001", "country": "India"}

    def get_profile(self): return self.profile
    def seed_demo_address(self, record=None): pass
    def get_product(self, id):
        if id != self.product["id"]: raise LookupError
        return self.product
    def get_address(self, id):
        if id != self.address["id"]: raise LookupError
        return self.address


class FakeCases:
    def __init__(self):
        self.cases = {}
        self.keys = {}

    def create_if_absent(self, key, digest, record):
        if key in self.keys:
            old_digest, old_id = self.keys[key]
            if old_digest != digest:
                raise IdempotencyConflict
            return self.cases[old_id]
        self.keys[key] = (digest, record["id"])
        self.cases[record["id"]] = record
        return record

    def replay_creation(self, key, digest):
        if key not in self.keys:
            return None
        previous_digest, id = self.keys[key]
        if previous_digest != digest:
            raise IdempotencyConflict
        return self.cases[id]

    def get(self, id): return self.cases.get(id)
    def list(self, product_id=None):
        return [row for row in self.cases.values() if not product_id or row["productId"] == product_id]


PAYLOAD = {"productId": "product-1", "addressId": "address-1",
           "issueSummary": "Leaking water", "description": "Water leaks below the device."}


def service():
    vault, store = FakeVault(), FakeCases()
    return CaseService(vault, store), vault, store


def test_duplicate_create_replays():
    cases, _, store = service()
    first = cases.create(PAYLOAD, "fictional-key-12345")
    second = cases.create(PAYLOAD, "fictional-key-12345")
    assert first["id"] == second["id"]
    assert first["status"] == "PROCESSING"
    assert len(store.cases) == 1


def test_same_key_changed_payload_conflicts():
    cases, _, _ = service()
    cases.create(PAYLOAD, "fictional-key-12345")
    with pytest.raises(IdempotencyConflict):
        cases.create({**PAYLOAD, "issueSummary": "Different issue"}, "fictional-key-12345")


def test_snapshot_survives_profile_edit():
    cases, vault, _ = service()
    created = cases.create(PAYLOAD, "fictional-key-12345")
    vault.profile["name"] = "Changed Name"
    vault.address["line1"] = "Changed Road"
    assert cases.get(created["id"])["factsSnapshot"]["profile"]["name"] == "Fictional User"
    assert cases.get(created["id"])["factsSnapshot"]["address"]["line1"] == "1 Fiction Lane"


def test_incomplete_profile_blocks_creation():
    cases, vault, store = service()
    vault.profile["phone"] = ""
    with pytest.raises(CaseValidationError) as failure:
        cases.create(PAYLOAD, "fictional-key-12345")
    assert "phone" in failure.value.field_errors
    assert not store.cases


def test_duplicate_create_replays_after_profile_changes():
    cases, vault, store = service()
    first = cases.create(PAYLOAD, "fictional-key-12345")
    vault.profile["phone"] = ""
    assert cases.create(PAYLOAD, "fictional-key-12345")["id"] == first["id"]
    assert len(store.cases) == 1


def test_no_time_preference_and_invalid_record_ids():
    cases, _, _ = service()
    with pytest.raises(CaseValidationError):
        cases.create({**PAYLOAD, "timePreference": "morning"}, "fictional-key-12345")
    with pytest.raises(CaseValidationError):
        cases.create({**PAYLOAD, "productId": "missing"}, "fictional-key-12345")


def test_record_identifiers_cannot_be_firestore_paths():
    with pytest.raises(ValueError):
        ComplaintInput.model_validate({**PAYLOAD, "productId": "collection/record"})


@pytest.mark.asyncio
async def test_case_http_conflict_and_profile_field_errors():
    class Sessions:
        def get(self, digest):
            return {"expires_at": datetime.now(timezone.utc) + timedelta(hours=1)} if digest == token_digest("fictional") else None

    vault = FakeVault()
    app = create_app(settings=Settings(), session_store=Sessions(), vault_store=vault, case_store=FakeCases())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://api.test") as client:
        assert (await client.post("/api/complaints", json=PAYLOAD)).status_code == 401
        client.cookies.set("__session", "fictional")
        headers = {"Idempotency-Key": "fictional-stable-key"}
        first = await client.post("/api/complaints", json=PAYLOAD, headers=headers)
        assert first.status_code == 200
        assert (await client.post("/api/complaints", json=PAYLOAD, headers=headers)).json()["id"] == first.json()["id"]
        conflict = await client.post("/api/complaints", json={**PAYLOAD, "description": "Different"}, headers=headers)
        assert conflict.status_code == 409
        vault.profile["phone"] = ""
        incomplete = await client.post("/api/complaints", json=PAYLOAD, headers={"Idempotency-Key": "fictional-new-key-2"})
        assert incomplete.status_code == 422 and "phone" in incomplete.json()["field_errors"]


def test_intake_contact_override_does_not_change_saved_profile():
    cases, vault, _ = service()
    created = cases.create({**PAYLOAD, 'contact': {'name': 'Visit Contact', 'phone': '9111111111',
        'email': 'visit@example.test'}}, 'complaint-contact-override')
    assert created['factsSnapshot']['profile']['phone'] == '9111111111'
    assert vault.profile['phone'] == '9999999999'
    assert vault.profile['name'] == 'Fictional User'
