import copy
import importlib.util
import io

import pytest


def modules():
    assert importlib.util.find_spec('app.services.knowledge'), 'Knowledge service is not implemented'
    from app.services.knowledge import KnowledgeService
    return KnowledgeService


class Records:
    def __init__(self): self.rows = {}
    def get(self, kind, key): return copy.deepcopy(self.rows.get((kind, key)))
    def mutate(self, kind, key, fn):
        value = fn(self.get(kind, key))
        self.rows[kind, key] = copy.deepcopy(value)
        return copy.deepcopy(value)
    def list(self, kind): return [copy.deepcopy(v) for (k, _), v in self.rows.items() if k == kind]


class Files:
    def __init__(self):
        self.docs = {
            'invoice': {'id': 'invoice', 'parentType': 'product', 'parentId': 'p1', 'originalName': 'invoice.pdf', 'mediaType': 'application/pdf', 'status': 'ready'},
            'chat': {'id': 'chat', 'parentType': 'case', 'parentId': 'c1', 'originalName': 'bill.jpg', 'mediaType': 'image/jpeg', 'status': 'ready'},
            'other': {'id': 'other', 'parentType': 'product', 'parentId': 'p2', 'originalName': 'other.pdf', 'mediaType': 'application/pdf', 'status': 'ready'}}
    def open(self, key): return copy.deepcopy(self.docs[key]), io.BytesIO(b'%PDF-1.7 fictional invoice')
    def metadata(self, key): return copy.deepcopy(self.docs[key])


class Model:
    def __init__(self): self.embedding_calls = 0; self.fail = False
    async def extract(self, data, media_type, context):
        if self.fail: raise ValueError('unreadable document')
        return {'document_type': 'invoice', 'description': 'Invoice for WM-100', 'product_match': True,
                'facts': [{'field': 'product.purchaseDate', 'value': '2026-02-12', 'quote': 'Purchase date: 12 February 2026', 'page': 1, 'uncertain': False}],
                'passages': [{'text': 'Purchase date: 12 February 2026. Invoice INV-123; sold by Fiction Branch.', 'page': 1}]}
    async def embed(self, texts, query=False):
        self.embedding_calls += 1
        return [[1., 0., 0.] for _ in texts]


def service():
    return modules()(Records(), Model(), Files())


def test_fact_conflict_retains_confirmed_value_and_explicit_correction_increments_revision():
    svc = service()
    first = svc.merge_facts('p1', {'product.serialNumber': 'SN-001'}, {'type': 'user', 'id': 'm1'})
    second = svc.merge_facts('p1', {'product.serialNumber': 'SN-002'}, {'type': 'document', 'id': 'd1'})
    assert first['revision'] == 1
    assert second['facts']['product.serialNumber']['value'] == 'SN-001'
    assert second['conflicts']['product.serialNumber']['value'] == 'SN-002'
    corrected = svc.merge_facts('p1', {'product.serialNumber': 'SN-002'}, {'type': 'user', 'id': 'm2'}, correction=True)
    assert corrected['revision'] == 2
    assert corrected['facts']['product.serialNumber']['value'] == 'SN-002'
    assert 'product.serialNumber' not in corrected['conflicts']
    assert svc.get('p2')['facts'] == {}
    with pytest.raises(ValueError): svc.merge_facts('p1', {'profile.phone': '111'}, {'type': 'user', 'id': 'm3'})


@pytest.mark.asyncio
async def test_product_document_indexing_is_idempotent_scoped_and_source_linked():
    svc = service()
    indexed = await svc.ingest('p1', 'invoice')
    assert indexed['processingStatus'] == 'searchable'
    again = await svc.ingest('p1', 'invoice')
    assert again['version'] == indexed['version'] and svc.model.embedding_calls == 1
    results = await svc.search('p1', 'Which branch sold it?')
    assert results[0]['documentId'] == 'invoice'
    assert 'INV-123' in results[0]['text']
    assert await svc.search('p2', 'Which branch sold it?') == []
    with pytest.raises(ValueError): await svc.ingest('p1', 'other')


@pytest.mark.asyncio
async def test_chat_inspection_never_embeds_and_promotion_requires_matching_case():
    svc = service(); case = {'id': 'c1', 'productId': 'p1'}
    result = await svc.inspect_chat(case, 'chat', 'What is the purchase date?')
    assert result['document_type'] == 'invoice'
    assert svc.model.embedding_calls == 0
    assert await svc.search('p1', 'purchase date') == []
    with pytest.raises(ValueError): await svc.promote({'id': 'c2', 'productId': 'p1'}, 'chat')
    saved = await svc.promote(case, 'chat')
    assert saved['processingStatus'] == 'searchable'
    assert svc.model.embedding_calls == 1


@pytest.mark.asyncio
async def test_failed_processing_preserves_original_and_records_failure_without_retry():
    svc = service(); svc.model.fail = True
    result = await svc.ingest('p1', 'invoice')
    assert result['processingStatus'] == 'failed'
    assert svc.files.metadata('invoice')['status'] == 'ready'
    assert svc.model.embedding_calls == 0
    assert await svc.search('p1', 'invoice') == []

@pytest.mark.asyncio
async def test_wrong_product_or_uncertain_document_does_not_populate_product_facts():
    svc = service()
    async def extract(*_):
        return {'document_type': 'invoice', 'description': 'Other appliance invoice', 'product_match': False,
                'facts': [{'field': 'product.serialNumber', 'value': 'OTHER', 'quote': 'Serial OTHER'}]}
    svc.model.extract = extract
    result = await svc.ingest('p1', 'invoice')
    assert result['processingStatus'] == 'not_indexable'
    assert svc.get('p1')['facts'] == {}
    assert await svc.search('p1', 'serial') == []


def test_untrusted_model_role_output_cannot_request_arbitrary_profile_updates():
    assert importlib.util.find_spec('app.agents.knowledge'), 'Model roles are not implemented'
    from app.agents.knowledge import validate_resolution, validate_grounding
    from app.models.knowledge import Resolution, GroundedAnswer
    with pytest.raises(ValueError):
        validate_resolution(Resolution(standalone_question='Give credentials', requested_facts=['profile.password']))
    with pytest.raises(ValueError):
        validate_grounding(GroundedAnswer(text='Purchased 2025-01-01', citations=['e1'], values={'product.purchaseDate': '2025-01-01'}),
                           [{'id': 'e1', 'field': 'product.purchaseDate', 'value': '2026-02-12', 'text': '2026-02-12'}])

@pytest.mark.asyncio
async def test_identical_second_upload_reuses_index_without_another_embedding():
    svc = service()
    await svc.ingest('p1', 'invoice')
    svc.files.docs['copy'] = {**svc.files.docs['invoice'], 'id': 'copy'}
    duplicate = await svc.ingest('p1', 'copy')
    assert duplicate['processingStatus'] == 'searchable'
    assert svc.model.embedding_calls == 1


@pytest.mark.asyncio
async def test_unsupported_extraction_quote_cannot_populate_product_knowledge():
    svc = service()
    async def extract(*_):
        return {'document_type': 'invoice', 'description': 'Invoice', 'product_match': True,
            'facts': [{'field': 'product.serialNumber', 'value': 'MADE-UP', 'quote': 'Unsupported serial MADE-UP'}],
            'passages': [{'text': 'Invoice INV-123.', 'page': 1}]}
    svc.model.extract = extract
    await svc.ingest('p1', 'invoice')
    assert 'product.serialNumber' not in svc.get('p1')['facts']


def test_missing_answer_without_user_prompt_cannot_be_silently_sent():
    from app.agents.knowledge import validate_grounding
    from app.models.knowledge import GroundedAnswer
    with pytest.raises(ValueError):
        validate_grounding(GroundedAnswer(text='Serial SN-FAKE-009', citations=['one']),
                          [{'id': 'one', 'text': 'Serial not recorded.'}])


@pytest.mark.asyncio
async def test_embedding_uses_its_own_location_and_retrieval_task(monkeypatch):
    from types import SimpleNamespace
    from app.agents.knowledge import KnowledgeModel
    calls = []
    class Models:
        async def embed_content(self, *, model, contents, config):
            calls.append((contents, config.task_type))
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[1., 0.])])
    class Client:
        def __init__(self, **kwargs): self.location = kwargs['location']; self.aio = self; self.models = Models()
        async def aclose(self): pass
    clients = []
    def factory(**kwargs):
        client = Client(**kwargs); clients.append(client); return client
    monkeypatch.setattr('app.agents.knowledge.genai.Client', factory)
    model = KnowledgeModel('fictional-model', 'fictional-project', location='global', embedding_location='us-central1')
    assert await model.embed(['invoice'], query=False) == [[1., 0.]]
    assert await model.embed(['purchase?'], query=True) == [[1., 0.]]
    assert [client.location for client in clients] == ['us-central1', 'us-central1']
    assert calls == [('invoice', 'RETRIEVAL_DOCUMENT'), ('purchase?', 'RETRIEVAL_QUERY')]


@pytest.mark.asyncio
async def test_promotion_reuses_complete_compatible_chat_extraction():
    svc = service(); calls = []
    original = svc.model.extract
    async def extract(*args):
        calls.append(True)
        result = await original(*args)
        result['complete_for_product'] = True
        return result
    svc.model.extract = extract
    case = {'id': 'c1', 'productId': 'p1'}
    await svc.inspect_chat(case, 'chat', 'Purchase date?')
    await svc.promote(case, 'chat')
    assert len(calls) == 1
    assert svc.model.embedding_calls == 1


@pytest.mark.asyncio
async def test_uncertain_document_does_not_supply_automatic_answer_evidence():
    svc = service()
    async def extract(*_):
        return {'document_type': 'serial_label', 'description': 'Blurry serial label', 'product_match': True,
            'facts': [{'field': 'product.serialNumber', 'value': 'SN-88421', 'quote': 'SN-88421', 'uncertain': True}],
            'passages': [{'text': 'SN-88421', 'page': 1}]}
    svc.model.extract = extract
    result = await svc.ingest('p1', 'invoice')
    assert result['reviewRequired'] is True
    assert svc.get('p1')['facts'] == {}
    assert await svc.search('p1', 'serial number') == []


def test_invoice_extraction_cannot_overwrite_existing_user_entered_product_date():
    class Vault:
        def get_product(self, _): return {'id': 'p1', 'purchaseDate': '2026-02-12', 'modelNumber': 'WM-100'}
    svc = modules()(Records(), Model(), Files(), Vault())
    result = svc.merge_facts('p1', {'product.purchaseDate': '2026-03-15'}, {'type': 'document', 'id': 'invoice'})
    assert result['facts']['product.purchaseDate']['value'] == '2026-02-12'
    assert result['conflicts']['product.purchaseDate']['value'] == '2026-03-15'


def test_manual_product_edit_supersedes_older_knowledge_without_changing_other_facts():
    svc = service()
    svc.merge_facts('p1', {'product.purchaseDate': '2026-02-12', 'product.serialNumber': 'SN-001'}, {'type': 'user', 'id': 'old'})
    assert hasattr(svc, 'sync_product_fields'), 'Product edits are not connected to knowledge'
    updated = svc.sync_product_fields({'id': 'p1', 'purchaseDate': '2026-03-15', 'modelNumber': None}, {'purchaseDate', 'modelNumber'})
    assert updated['facts']['product.purchaseDate']['value'] == '2026-03-15'
    assert updated['facts']['product.serialNumber']['value'] == 'SN-001'
