import pytest
from backend.tests.unit.test_vault import service
from backend.tests.unit.test_cases import service as case_service, PAYLOAD


def test_sourced_model_suggestions_cover_each_type_and_match_brand_pairs():
    vault = service()
    catalog = vault.catalog()
    models = catalog.get('models', [])
    assert {m['categoryId'] for m in models} == {c['id'] for c in catalog['categories']}
    pairs = {(c['id'], b['id']) for c in catalog['categories'] for b in c['brands']}
    assert all((m['categoryId'], m['brandId']) in pairs for m in models)
    assert all(m['source'].startswith('https://') and m['checkedOn'] for m in models)
    assert any(m['brandId'] == 'oneplus' and m['number'] == 'CPH2649' for m in models)


def test_model_is_optional_and_separate_from_nickname():
    vault = service()
    base = {'categoryId': 'smartphone', 'brandId': 'oneplus', 'nickname': 'Work phone'}
    saved = vault.create_product({**base, 'modelNumber': ' CPH2649 '})
    assert saved['modelNumber'] == 'CPH2649'
    assert saved['displayName'] == 'Work phone'
    assert vault.update_product(saved['id'], {'modelNumber': None})['modelNumber'] is None
    assert vault.create_product(base)['modelNumber'] is None
    assert vault.create_product({**base, 'modelNumber': 'MY-OLD-DEVICE'})['modelNumber'] == 'MY-OLD-DEVICE'
    with pytest.raises(ValueError): vault.create_product({**base, 'modelNumber': 'x' * 121})


def test_agent_snapshot_uses_actual_model_instead_of_nickname():
    cases, vault, _ = case_service()
    vault.product.update(modelNumber='CPH2649', displayName='Work phone')
    case = cases.create(PAYLOAD, 'actual-model-key-12345')
    assert case['factsSnapshot']['product']['model'] == 'CPH2649'
    assert case['factsSnapshot']['product']['displayName'] == 'Work phone'
