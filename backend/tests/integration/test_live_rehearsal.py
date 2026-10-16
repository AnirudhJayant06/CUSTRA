"""Opt-in: four live Vertex answers; all persistence stays in a local emulator."""

import asyncio
import os
import uuid

import httpx
import pytest

from app.config import Settings
from app.main import create_app
from app.services.a2a_gateway import A2AGateway
from app.services.auth import hash_password
from app.services.repository import FirestoreCaseStore, FirestoreSessionStore, FirestoreVaultStore


@pytest.mark.asyncio
async def test_live_four_answer_case_with_local_firestore_and_a2a():
    if os.getenv('CUSTRA_RUN_LIVE_REHEARSAL') != '1':
        pytest.skip('Opt in only after the single Vertex answer passes; maximum four live answers')
    host = os.getenv('FIRESTORE_EMULATOR_HOST', '')
    if not host.startswith(('127.0.0.1:', 'localhost:', '[::1]:')):
        pytest.fail('A loopback Firestore emulator is required; no production persistence is allowed')
    project = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project:
        pytest.fail('An explicit authorized Vertex project is required')
    from main import create_app as business_app
    from store import FirestoreReplayStore

    namespace = f'test-{uuid.uuid4().hex}'
    case_store = FirestoreCaseStore('demo-custra-tests', namespace)
    simulator_store = FirestoreReplayStore('demo-custra-tests', namespace)
    settings = Settings(project_id=project, model_location='global', secure_cookies=False,
                        demo_username='fictional-reviewer', password_hash=hash_password('fictional-passphrase'))
    app = create_app(settings=settings,
                     session_store=FirestoreSessionStore('demo-custra-tests', namespace),
                     vault_store=FirestoreVaultStore('demo-custra-tests', namespace), case_store=case_store)
    simulator = business_app('http://business.test', simulator_store)
    try:
        async with asyncio.timeout(180), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=simulator), base_url='http://business.test', timeout=8,
        ) as business, httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://api.test') as client:
            app.state.cases.gateway = A2AGateway('http://business.test', business)
            assert (await client.post('/api/auth/login', json={
                'username': 'fictional-reviewer', 'password': 'fictional-passphrase'})).status_code == 200
            assert (await client.patch('/api/profile', json={
                'name': 'Fictional Reviewer', 'phone': '9999999999', 'email': 'fictional@example.test'})).status_code == 200
            address = (await client.get('/api/addresses')).json()[0]
            product = (await client.post('/api/products', json={
                'categoryId': 'smartphone', 'brandId': 'samsung', 'displayName': 'Fictional Phone'})).json()
            created = await client.post('/api/complaints', headers={'Idempotency-Key': 'fictional-live-creation-key'}, json={
                'productId': product['id'], 'addressId': address['id'], 'issueSummary': 'Device stops',
                'description': 'The fictional device stops during use.'})
            assert created.status_code == 200
            case = created.json()
            path = f"/api/complaints/{case['id']}"
            for _ in range(5):
                step = await client.post(f'{path}/advance', json={'expectedVersion': case['currentVersion']})
                assert step.status_code == 200
                case = step.json()
                assert case['status'] != 'ERROR', 'Live answer or A2A step failed; no automatic model retry'
            assert case['status'] == 'AWAITING_APPOINTMENT'
            events = (await client.get(f'{path}/events')).json()
            assert len(events) == 9 and sum(event['role'] == 'consumer' for event in events) == 4
            slot = (await client.get(f'{path}/slots')).json()[0]
            booked = await client.post(f'{path}/appointment', headers={'Idempotency-Key': 'fictional-live-booking-key'},
                                       json={'slotId': slot['id']})
            assert booked.status_code == 200 and booked.json()['status'] == 'BOOKED'
            assert (await client.post(f'{path}/confirm-resolution', json={'confirmed': False})).status_code == 409
            closed = await client.post(f'{path}/confirm-resolution', json={'confirmed': True})
            assert closed.status_code == 200 and closed.json()['status'] == 'CLOSED'
            assert (await client.post('/api/auth/logout')).status_code == 200
    finally:
        for row in case_store.root.collection('cases').stream():
            for event in row.reference.collection('events').stream(): event.reference.delete()
        for collection in ('sessions', 'account', 'addresses', 'products', 'cases', 'creation_keys', 'operations'):
            for row in case_store.root.collection(collection).stream(): row.reference.delete()
        for collection in ('cases', 'operations'):
            for row in simulator_store.root.collection(collection).stream(): row.reference.delete()
