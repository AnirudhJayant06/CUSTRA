from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from backend.tests.unit.test_vault import service
from backend.tests.unit.test_cases import service as case_service, PAYLOAD


def test_optional_nickname_defaults_and_warranty_uses_calendar_months():
    vault = service()
    category = vault.catalog()['categories'][0]
    brand = category['brands'][0]
    saved = vault.create_product({'categoryId': category['id'], 'brandId': brand['id'],
                                 'nickname': '  ', 'purchaseDate': '2024-02-29', 'warrantyMonths': 12})
    assert saved['displayName'] == f"{brand['name']} {category['name']}"
    assert saved['warrantyExpiry'] == '2025-02-28'
    renamed = vault.update_product(saved['id'], {'nickname': ' Bedroom phone '})
    assert renamed['displayName'] == 'Bedroom phone'
    assert renamed['nickname'] == 'Bedroom phone'
    cleared = vault.update_product(saved['id'], {'nickname': ''})
    assert cleared['displayName'] == f"{brand['name']} {category['name']}"


def test_warranty_rejects_invalid_duration_and_preserves_legacy_names():
    vault = service()
    cat = vault.catalog()['categories'][0]
    base = {'categoryId': cat['id'], 'brandId': cat['brands'][0]['id'], 'displayName': 'Legacy model'}
    old = vault.create_product({**base, 'warrantyExpiry': '2028-01-10'})
    assert old['displayName'] == 'Legacy model' and old['warrantyExpiry'] == '2028-01-10'
    for value in (-1, 0, 121, 1.5, True):
        with pytest.raises(ValueError):
            vault.create_product({**base, 'warrantyMonths': value})


def test_default_address_must_exist_and_preserves_contact_fields():
    vault = service()
    vault.save_profile({'name': 'Demo', 'phone': '00000', 'email': 'demo@example.test'})
    address = vault.create_address({'label': 'Home', 'line1': 'Example', 'city': 'Pune',
                                    'region': 'Maharashtra', 'postalCode': '411001', 'country': 'India'})
    vault.set_default_address(address['id'])
    assert vault.get_profile()['defaultAddressId'] == address['id']
    assert vault.get_profile()['name'] == 'Demo'
    with pytest.raises(LookupError): vault.set_default_address('missing')


def test_single_description_and_preference_persist_without_booking():
    from app.services.demo_schedule import demo_schedule
    schedule = demo_schedule()
    selected = next(s for s in schedule if s['available'])
    cases, _, store = case_service()
    payload = {k: v for k, v in PAYLOAD.items() if k != 'issueSummary'}
    payload.update(preferredDate=selected['date'], preferredSlotId=selected['id'])
    saved = cases.create(payload, 'mobile-preference-key')
    assert saved['issueSummary'] == payload['description'][:120]
    assert saved['preferredSlotId'] == selected['id']
    assert saved['status'] == 'PROCESSING' and 'appointment' not in saved
    assert cases.create(payload, 'mobile-preference-key')['id'] == saved['id']
    unavailable = next(s for s in schedule if not s['available'])
    with pytest.raises(ValueError):
        cases.create({**payload, 'preferredSlotId': unavailable['id']}, 'another-preference-key')
    with pytest.raises(ValueError):
        cases.create({**payload, 'preferredDate': '2000-01-01'}, 'expired-preference-key')


def test_api_and_simulator_share_available_schedule():
    from app.services.demo_schedule import demo_schedule
    path = Path('manufacturer-agent/app/demo_schedule.py')
    spec = importlib.util.spec_from_file_location('business_schedule', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    current = datetime(2026, 10, 17, 10, tzinfo=timezone.utc)
    a = demo_schedule(current)
    assert a == module.demo_schedule(current)
    assert len(a) == 63
    assert all(s['timezone'] == 'Asia/Kolkata' for s in a)
    assert {s['available'] for s in a} == {True, False}
    assert all(s['date'] > '2026-10-17' for s in a)


def test_legacy_case_payload_digest_is_unchanged_and_preference_is_immutable():
    import hashlib
    import json
    cases, _, store = case_service()
    saved = cases.create(PAYLOAD, 'legacy-case-key-12345')
    assert store.keys['legacy-case-key-12345'][0] == hashlib.sha256(json.dumps(PAYLOAD, sort_keys=True).encode()).hexdigest()
    assert saved['factsSnapshot']['issue']['description'] == PAYLOAD['description']


@pytest.mark.asyncio
async def test_availability_and_default_address_routes_require_session():
    from app.main import create_app
    from app.config import Settings
    from app.services.auth import token_digest
    from backend.tests.unit.test_vault import FakeVaultStore
    class Sessions:
        def get(self, digest):
            if digest == token_digest('mobile-token'):
                return {'expires_at': datetime.now(timezone.utc) + timedelta(hours=1), 'revoked': False}
    app = create_app(settings=Settings(), session_store=Sessions(), vault_store=FakeVaultStore())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://api.test') as client:
        assert (await client.get('/api/availability')).status_code == 401
        assert (await client.put('/api/profile/default-address/demo-address')).status_code == 401
        client.cookies.set('__session', 'mobile-token')
        response = await client.get('/api/availability')
        assert response.status_code == 200 and len(response.json()['slots']) == 63
        assert response.headers['cache-control'] == 'private, no-store'
        assert (await client.put('/api/profile/default-address/missing')).status_code == 404
        assert (await client.put('/api/profile/default-address/demo-address')).status_code == 200
