import os
import uuid

import httpx
import pytest

from app.config import Settings
from app.main import create_app
from app.services.auth import hash_password
from app.services.repository import FirestoreCaseStore, FirestoreSessionStore, FirestoreVaultStore


@pytest.mark.asyncio
async def test_session_vault_and_case_snapshot_survive_app_recreation():
    host = os.getenv("FIRESTORE_EMULATOR_HOST", "")
    if not host: pytest.skip("Firestore emulator is not configured")
    if not host.startswith(("127.0.0.1:", "localhost:", "[::1]:")): pytest.fail("A loopback emulator is required")
    namespace = f"test-{uuid.uuid4().hex}"
    settings = Settings(project_id="demo-custra-tests", demo_username="fictional-reviewer",
                        password_hash=hash_password("fictional-passphrase"), secure_cookies=False)
    def application():
        return create_app(settings=settings,
                          session_store=FirestoreSessionStore(settings.project_id, namespace=namespace),
                          vault_store=FirestoreVaultStore(settings.project_id, namespace=namespace),
                          case_store=FirestoreCaseStore(settings.project_id, namespace=namespace))
    first = application()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=first), base_url="http://api.test") as client:
            assert (await client.post("/api/auth/login", json={"username": "fictional-reviewer", "password": "fictional-passphrase"})).status_code == 200
            profile = {"name": "Fictional User", "phone": "9999999999", "email": "fictional@example.test"}
            assert (await client.patch("/api/profile", json=profile)).status_code == 200
            assert len((await client.get("/api/addresses")).json()) == 1
            address = (await client.post("/api/addresses", json={"label": "Home", "line1": "1 Fiction Lane", "city": "Pune",
                                                                 "region": "Maharashtra", "postalCode": "411001", "country": "India"})).json()
            product = (await client.post("/api/products", json={"categoryId": "smartphone", "brandId": "samsung", "displayName": "Fictional Phone"})).json()
            case_response = await client.post("/api/complaints", headers={"Idempotency-Key": "fictional-stable-key"}, json={
                "productId": product["id"], "addressId": address["id"], "issueSummary": "Stops working", "description": "Fictional device stops."})
            assert case_response.status_code == 200
            case_id = case_response.json()["id"]
            second = application()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=second), base_url="http://api.test", cookies=client.cookies) as resumed:
                assert (await resumed.get("/api/auth/session")).status_code == 200
                assert (await resumed.get("/api/profile")).json()["name"] == "Fictional User"
                assert len((await resumed.get("/api/addresses")).json()) == 2
                assert len((await resumed.get("/api/products")).json()) == 1
                await resumed.patch("/api/profile", json={**profile, "name": "Changed Fictional Name"})
                saved_case = (await resumed.get(f"/api/complaints/{case_id}")).json()
                assert saved_case["factsSnapshot"]["profile"]["name"] == "Fictional User"
                newer = await resumed.post('/api/complaints', headers={'Idempotency-Key': 'fictional-after-profile-edit'}, json={
                    'productId': product['id'], 'addressId': address['id'], 'issueSummary': 'Another fictional issue',
                    'description': 'A new case uses the edited profile.'})
                assert newer.status_code == 200
                assert newer.json()['factsSnapshot']['profile']['name'] == 'Changed Fictional Name'
                assert (await resumed.post("/api/auth/logout")).status_code == 200
            assert (await client.get("/api/auth/session")).status_code == 401
    finally:
        root = first.state.vault.store.root
        for collection in ("sessions", "account", "addresses", "products", "cases", "creation_keys"):
            for row in root.collection(collection).stream(): row.reference.delete()
