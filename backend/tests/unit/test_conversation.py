import copy
import importlib.util
from datetime import datetime, timezone

import pytest
from app.models.knowledge import Resolution, GroundedAnswer
from app.models.exchange import ExchangeResponse
from app.services.leases import CaseConflict, acquire_lease, check_lease


class Store:
    def __init__(self):
        self.case = {'id': 'c1', 'productId': 'p1', 'status': 'PROCESSING', 'scenarioId': 'natural',
            'currentVersion': 0, 'stepIndex': 1, 'eventSequence': 1, 'businessStage': 'details',
            'pendingQuestion': {'display_text': 'And when did you buy it?', 'next_stage': 'details'},
            'factsSnapshot': {'product': {'model': 'WM-100'}, 'profile': {'phone': '111'}, 'issue': {'description': 'Leak'}}}
        self.operations = {}; self.messages = []
    def get(self, _): return copy.deepcopy(self.case)
    def events(self, _, after=0): return copy.deepcopy(self.messages)
    def acquire_advance(self, _, version):
        key = f"c1-advance-{self.case['stepIndex']}"
        op = acquire_lease(self.case, self.operations.get(key, {'operationId': key}), version, datetime.now(timezone.utc))
        self.operations[key] = op
        return {'case': copy.deepcopy(self.case), 'operation': copy.deepcopy(op)}
    def save_answer(self, lease, answer): self.operations[lease['operation']['operationId']]['savedAnswer'] = copy.deepcopy(answer)
    def save_preparation(self, lease, preparation): self.operations[lease['operation']['operationId']]['preparation'] = copy.deepcopy(preparation)
    def commit_advance(self, lease, changes, events):
        check_lease(self.case, self.operations[lease['operation']['operationId']], lease['operation'], datetime.now(timezone.utc))
        self.case.update(changes); self.case['stepIndex'] += 1; self.case['currentVersion'] += 1
        self.messages.extend(events); self.operations[lease['operation']['operationId']]['leaseToken'] = None
        return self.get('c1')
    def fail_advance(self, lease):
        self.case.update(status='ERROR', recoveryPhase='advance'); self.case['currentVersion'] += 1
        self.operations[lease['operation']['operationId']]['leaseToken'] = None
        return self.get('c1')
    def interact(self, _, version, changes, text=None):
        if version != self.case['currentVersion']: raise CaseConflict('Changed')
        self.case.update(changes); self.case['currentVersion'] += 1
        if text: self.messages.append({'role': 'user', 'displayText': text, 'eventId': str(version), 'sequence': len(self.messages)+2})
        return self.get('c1')


class Knowledge:
    def __init__(self): self.facts = {}; self.saved = []
    def get(self, _): return {'revision': 1, 'facts': self.facts, 'conflicts': {}}
    async def search(self, *_): return []
    def merge_facts(self, product, facts, source, correction=False):
        self.saved.append((product, facts)); self.facts.update({k: {'value': v, 'source': source} for k, v in facts.items()})
    def documents(self, _): return []


class Model:
    def __init__(self, field='product.purchaseDate'): self.field = field
    async def resolve(self, question, context):
        return Resolution(standalone_question='What is the purchase date for WM-100?', requested_facts=[self.field])
    async def compose(self, question, evidence):
        return GroundedAnswer(text=evidence[0]['value'], citations=[evidence[0]['id']], values={self.field: evidence[0]['value']})


class Gateway:
    def __init__(self): self.requests = []
    async def exchange(self, request):
        self.requests.append(request)
        return ExchangeResponse(display_text='Where should the visit take place?', next_stage='location', context_id='ctx')


def service(field='product.purchaseDate'):
    assert importlib.util.find_spec('app.services.conversation'), 'Natural conversation is not implemented'
    from app.services.conversation import ConversationService
    return ConversationService(Store(), Knowledge(), Model(field), Gateway().exchange)


@pytest.mark.asyncio
async def test_unknown_purchase_date_is_deferred_without_inventing_a_fact():
    svc = service()
    answered = await svc.advance('c1', 0)
    assert answered['status'] == 'PROCESSING'
    assert svc.knowledge.saved == []
    assert svc.exchange.__self__.requests[-1].data['deferred'] is True


@pytest.mark.asyncio
async def test_phone_answer_updates_complaint_snapshot_only():
    svc = service('profile.phone')
    svc.store.case['factsSnapshot']['profile']['phone'] = ''
    svc.store.case.update(status='AWAITING_USER', pendingUserRequest={'kind': 'fact', 'fields': ['profile.phone']})
    saved = await svc.submit_input('c1', 0, '999')
    assert saved['factsSnapshot']['profile']['phone'] == '999'
    assert svc.knowledge.saved == []


@pytest.mark.asyncio
async def test_previously_paused_case_resumes_without_a_correction_form():
    svc = service()
    svc.store.case['status'] = 'PAUSED'
    answered = await svc.advance('c1', 0)
    assert answered['status'] == 'PROCESSING'
    assert svc.exchange.__self__.requests[-1].action == 'answer'


def test_operation_retry_limit_cannot_reset_after_reopen():
    case = {'currentVersion': 0, 'status': 'ERROR', 'recoveryPhase': 'advance'}
    op = {'operationId': 'same-op', 'attemptCount': 3}
    with pytest.raises(CaseConflict, match='retry|Retry|attempt'):
        acquire_lease(case, op, 0, datetime.now(timezone.utc))


@pytest.mark.asyncio
async def test_unrelated_purchase_date_cannot_be_submitted_for_an_address_question():
    svc = service('address.line1')
    svc.store.case.update(status='AWAITING_USER', pendingUserRequest={'kind': 'fact', 'fields': ['address.line1']})
    with pytest.raises(ValueError, match='Only the detail'):
        await svc.submit_input('c1', 0, '2026-03-15', {'product.purchaseDate': '2026-03-15'})
    assert svc.knowledge.saved == []


@pytest.mark.asyncio
async def test_chat_extracted_fact_is_not_treated_as_user_correction():
    svc = service()
    svc.knowledge.facts['product.purchaseDate'] = {'value': '2026-02-12', 'source': {'type': 'user'}}
    svc.store.case.update(status='AWAITING_USER', pendingUserRequest={'kind': 'fact', 'fields': ['product.purchaseDate']})
    async def inspect(*_):
        return {'product_match': True, 'document_type': 'invoice', 'passages': [{'text': 'Purchased 2026-03-15', 'page': 1}],
            'facts': [{'field': 'product.purchaseDate', 'value': '2026-03-15', 'quote': 'Purchased 2026-03-15', 'page': 1, 'uncertain': False}]}
    svc.knowledge.inspect_chat = inspect
    merges = []
    def merge(product, facts, source, correction=False): merges.append((source['type'], correction))
    svc.knowledge.merge_facts = merge
    await svc.submit_input('c1', 0, '', document_id='chat-doc')
    assert merges == [('document', False)]


@pytest.mark.asyncio
async def test_new_product_registration_fact_can_be_learned_without_a_question_mapping():
    svc = service('product.details.installation_date')
    svc.store.case.update(status='AWAITING_USER', pendingUserRequest={'kind': 'fact', 'fields': ['product.details.installation_date']})
    saved = await svc.submit_input('c1', 0, '2026-03-15')
    assert svc.knowledge.saved[0][1] == {'product.details.installation_date': '2026-03-15'}
    answered = await svc.advance('c1', saved['currentVersion'])
    assert answered['status'] == 'PROCESSING'


def test_preferred_visit_fact_contains_saved_time_not_internal_slot_identifier():
    from app.services.conversation import snapshot_facts
    facts = snapshot_facts({'factsSnapshot': {}, 'preferredDate': '2026-10-20', 'preferredSlotId': 'private-slot',
        'preferredSlot': {'start': '2026-10-20T10:00:00+05:30', 'end': '2026-10-20T12:00:00+05:30'}})
    assert facts['appointment.preference'] == '20 October 2026, 10:00–12:00 IST'
    assert 'private-slot' not in facts['appointment.preference']


@pytest.mark.asyncio
async def test_saved_address_continues_without_document_retrieval_or_model_answer():
    svc = service('address.line1')
    svc.store.case['pendingQuestion']['display_text'] = 'Where should the technician visit?'
    svc.store.case['factsSnapshot']['address'] = {'line1': '10 Fiction Street', 'city': 'Pune', 'postal_code': '411001'}
    async def broken(*_): raise ValueError('Unavailable composition')
    svc.model.compose = broken
    answered = await svc.advance('c1', 0)
    assert answered['status'] == 'PROCESSING'
    assert '10 Fiction Street' in svc.exchange.__self__.requests[-1].data['text']
    assert not svc.exchange.__self__.requests[-1].data.get('deferred')


@pytest.mark.asyncio
async def test_failed_question_resolution_is_bounded_and_defers_without_inventing_values():
    svc = service()
    calls = []
    async def broken(*_): calls.append(1); raise ValueError('Resolver failed')
    svc.model.resolve = broken
    answered = await svc.advance('c1', 0)
    assert answered['status'] == 'PROCESSING'
    assert len(calls) == 3
    data = svc.exchange.__self__.requests[-1].data
    assert data['deferred'] is True and 'technician' in data['text'].lower()
    assert not data.get('values')
    assert answered['deferredQuestions'][0]['question'] == 'And when did you buy it?'


@pytest.mark.asyncio
async def test_missing_fact_does_not_require_an_unrelated_date_to_continue():
    svc = service('address.line1')
    svc.store.case['pendingQuestion']['display_text'] = 'Where should the technician visit?'
    answered = await svc.advance('c1', 0)
    assert answered['status'] == 'PROCESSING'
    assert svc.exchange.__self__.requests[-1].data['deferred'] is True
    assert svc.knowledge.saved == []
    assert answered['deferredQuestions'][0]['fields'] == ['address.line1']


@pytest.mark.asyncio
async def test_deferral_replays_identical_payload_after_lost_business_reply():
    svc = service()
    requests = []
    real = svc.exchange
    async def lost(request):
        requests.append(request.model_dump())
        if len(requests) == 1: raise TimeoutError('Reply lost')
        return await real(request)
    svc.exchange = lost
    failed = await svc.advance('c1', 0)
    result = await svc.advance('c1', failed['currentVersion'])
    assert result['status'] == 'PROCESSING'
    assert requests[0] == requests[1] and requests[0]['data']['deferred']


def test_old_exhausted_preparation_gets_one_recovery_but_sent_outcomes_do_not():
    case = {'scenarioId': 'natural', 'currentVersion': 0, 'status': 'ERROR', 'recoveryPhase': 'advance'}
    old = {'operationId': 'old-step', 'attemptCount': 3}
    recovered = acquire_lease(case, old, 0, datetime.now(timezone.utc))
    assert recovered['legacyQuestionRecovery'] is True
    recovered['leaseToken'] = None
    with pytest.raises(CaseConflict): acquire_lease(case, recovered, 0, datetime.now(timezone.utc))
    with pytest.raises(CaseConflict): acquire_lease(case, {**old, 'sendStarted': True}, 0, datetime.now(timezone.utc))


@pytest.mark.asyncio
async def test_model_budgets_survive_lost_business_reply_and_do_not_re_resolve():
    svc = service('address.line1')
    svc.store.case['factsSnapshot']['address'] = {'line1': '10 Fiction Street'}
    counts = {'resolve': 0, 'compose': 0}
    original = svc.model.resolve
    async def resolve(*args): counts['resolve'] += 1; return await original(*args)
    async def compose(*_): counts['compose'] += 1; raise ValueError('Bad formatting')
    svc.model.resolve = resolve; svc.model.compose = compose
    real = svc.exchange; calls = []
    async def lost(request):
        calls.append(request)
        if len(calls) == 1: raise TimeoutError('Lost reply')
        return await real(request)
    svc.exchange = lost
    failed = await svc.advance('c1', 0)
    await svc.advance('c1', failed['currentVersion'])
    assert counts == {'resolve': 1, 'compose': 3}
    assert calls[0].model_dump() == calls[1].model_dump()


@pytest.mark.asyncio
async def test_preparation_timeout_is_finite_and_persists_consumed_attempt():
    import asyncio
    svc = service()
    lease = svc.store.acquire_advance('c1', 0)
    calls = []
    async def slow():
        calls.append(1)
        await asyncio.sleep(10)
    result = await svc._attempt(lease, 'compose', slow, asyncio.get_running_loop().time() + .01)
    assert result is None and len(calls) == 1
    assert svc.store.operations[lease['operation']['operationId']]['preparation']['attempts']['compose'] == 1


@pytest.mark.asyncio
async def test_full_saved_address_with_internal_citation_is_sent_without_product_search():
    svc = service()
    svc.store.case['pendingQuestion']['display_text'] = 'Where should the technician visit?'
    fields = ['address.line1', 'address.city', 'address.postal_code']
    values = dict(zip(fields, ['10 Fiction Street', 'Pune', '411001']))
    svc.store.case['factsSnapshot']['address'] = {'line1': values[fields[0]], 'city': 'Pune', 'postal_code': '411001'}
    def unavailable(_): raise AssertionError('Address must not depend on product knowledge')
    svc.knowledge.get = unavailable
    async def resolve(*_): return Resolution(standalone_question='Where should the technician visit?', requested_facts=fields)
    async def compose(*_): return GroundedAnswer(text='10 Fiction Street, Pune, 411001 [fact:address.line1]', values=values, citations=[f'fact:{field}' for field in fields])
    svc.model.resolve = resolve; svc.model.compose = compose
    result = await svc.advance('c1', 0)
    assert result['status'] == 'PROCESSING'
    data = svc.exchange.__self__.requests[-1].data
    assert data['text'] == '10 Fiction Street, Pune, 411001'
    assert data['values'] == values and not data.get('deferred')


@pytest.mark.asyncio
async def test_consented_document_is_reported_as_shared_not_deferred():
    svc = service()
    svc.store.case['sharingConsent'] = {'documentId': 'invoice', 'version': 'v1', 'filename': 'invoice.pdf', 'mediaType': 'application/pdf'}
    async def resolve(*_): return Resolution(standalone_question='Send the invoice', requires_document=True, document_type='invoice')
    requests = []
    async def acknowledge(request):
        requests.append(request)
        return ExchangeResponse(display_text='Received', next_stage='location', context_id='ctx', attachment_receipt='v1')
    svc.model.resolve = resolve; svc.exchange = acknowledge
    answered = await svc.advance('c1', 0)
    assert answered['status'] == 'PROCESSING'
    assert not requests[0].data.get('deferred')
    assert 'shared' in requests[0].data['text'].lower()
