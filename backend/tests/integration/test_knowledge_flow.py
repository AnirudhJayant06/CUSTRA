"""Real local Firestore persistence + injected model/file storage. No cloud calls."""
import os
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import pytest

from app.config import Settings
from app.main import create_app
from app.services.repository import FirestoreCaseStore, FirestoreVaultStore, FirestoreDocumentStore
from app.services.records import FirestoreRecords
from app.services.knowledge import KnowledgeService
from app.services.a2a_gateway import A2AGateway
from backend.tests.support.knowledge_fixtures import FixtureModel
from backend.tests.unit.test_files import FakeBucket
from backend.tests.integration.test_agent_boundary import business_app


@pytest.mark.asyncio
async def test_local_persisted_knowledge_registration_and_booking():
    host = os.getenv('FIRESTORE_EMULATOR_HOST', '')
    if not host: pytest.skip('Loopback Firestore emulator required')
    assert host.startswith(('127.0.0.1:', 'localhost:')), 'Never use a cloud database in this test'
    namespace = 'knowledge-' + uuid.uuid4().hex
    project = 'demo-custra-tests'
    cases = FirestoreCaseStore(project, namespace)
    records = FirestoreRecords(project, namespace)
    class Sessions:
        def get(self, _): return {'revoked': False, 'expires_at': datetime.now(timezone.utc)+timedelta(hours=1)}
    model = FixtureModel()
    app = create_app(settings=Settings(project_id=project, secure_cookies=False), session_store=Sessions(),
        vault_store=FirestoreVaultStore(project, namespace), case_store=cases,
        file_store=FirestoreDocumentStore(project, namespace), file_bucket=FakeBucket(),
        knowledge_records=records, knowledge_model=model)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=business_app()), base_url='http://business.test') as business, \
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://api.test') as client:
            client.cookies.set('__session', 'fictional-session')
            app.state.cases.gateway = A2AGateway('http://business.test', business)
            await client.patch('/api/profile', json={'name': 'Fiction User', 'phone': '9000000000', 'email': 'fiction@example.test'})
            product = (await client.post('/api/products', json={'categoryId': 'smartphone', 'brandId': 'samsung', 'modelNumber': 'WM-100'})).json()
            upload = await client.post(f"/api/products/{product['id']}/documents", files={'file': ('invoice.pdf', b'%PDF-1.7 fictional invoice', 'application/pdf')})
            assert upload.status_code == 200
            assert upload.json()['processingStatus'] == 'searchable'
            fresh = KnowledgeService(FirestoreRecords(project, namespace), FixtureModel(), app.state.files, app.state.vault)
            assert fresh.get(product['id'])['facts']['product.purchaseDate']['value'] == '2026-02-12'
            assert (await fresh.search(product['id'], 'Which branch?'))[0]['documentId'] == upload.json()['id']
            address = (await client.get('/api/addresses')).json()[0]
            response = await client.post('/api/complaints', headers={'Idempotency-Key': namespace}, json={
                'productId': product['id'], 'addressId': address['id'], 'description': 'Fictional leak',
                'contact': {'name': 'Visit User', 'phone': '9111111111', 'email': 'visit@example.test'}})
            assert response.status_code == 200
            case = response.json(); path = f"/api/complaints/{case['id']}"
            assert (await client.get('/api/profile')).json()['phone'] == '9000000000'
            for _ in range(6):
                response = await client.post(f'{path}/advance', json={'expectedVersion': case['currentVersion']})
                assert response.status_code == 200
                case = response.json()
                assert case['status'] != 'ERROR'
            assert case['status'] == 'AWAITING_APPOINTMENT'
            assert len((await client.get(f'{path}/events')).json()) == 11
            booked = await client.post(f'{path}/appointment', headers={'Idempotency-Key': namespace+'-book'}, json={'slotId': case['slots'][0]['id']})
            assert booked.status_code == 200 and booked.json()['status'] == 'BOOKED'
            assert (await client.post(f'{path}/confirm-resolution', json={'confirmed': True})).json()['status'] == 'CLOSED'
            assert (await client.patch(f"/api/products/{product['id']}", json={'purchaseDate': '2026-03-15'})).status_code == 200
            assert fresh.get(product['id'])['facts']['product.purchaseDate']['value'] == '2026-03-15'
    finally:
        cases.client.recursive_delete(cases.root)
