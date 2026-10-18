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
async def test_missing_information_hands_off_then_reuses_user_fact_without_question_mapping():
    svc = service()
    pending = await svc.advance('c1', 0)
    assert pending['status'] == 'AWAITING_USER'
    assert pending['pendingUserRequest']['fields'] == ['product.purchaseDate']
    saved = await svc.submit_input('c1', pending['currentVersion'], '2026-02-12')
    assert saved['status'] == 'PROCESSING'
    answered = await svc.advance('c1', saved['currentVersion'])
    assert answered['businessStage'] == 'location'
    assert svc.knowledge.saved[0][1] == {'product.purchaseDate': '2026-02-12'}
    assert any(e.get('displayText') == '2026-02-12' for e in svc.store.messages)


@pytest.mark.asyncio
async def test_phone_answer_updates_complaint_snapshot_only():
    svc = service('profile.phone')
    svc.store.case['factsSnapshot']['profile']['phone'] = ''
    pending = await svc.advance('c1', 0)
    saved = await svc.submit_input('c1', pending['currentVersion'], '999')
    assert saved['factsSnapshot']['profile']['phone'] == '999'
    assert svc.knowledge.saved == []


@pytest.mark.asyncio
async def test_pause_blocks_next_advance_and_resume_keeps_same_complaint():
    svc = service()
    paused = svc.pause('c1', 0)
    assert paused['status'] == 'PAUSED'
    with pytest.raises(CaseConflict): await svc.advance('c1', paused['currentVersion'])
    resumed = svc.resume('c1', paused['currentVersion'])
    assert resumed['id'] == 'c1' and resumed['status'] == 'PROCESSING'


def test_operation_retry_limit_cannot_reset_after_reopen():
    case = {'currentVersion': 0, 'status': 'ERROR', 'recoveryPhase': 'advance'}
    op = {'operationId': 'same-op', 'attemptCount': 3}
    with pytest.raises(CaseConflict, match='retry|Retry|attempt'):
        acquire_lease(case, op, 0, datetime.now(timezone.utc))


@pytest.mark.asyncio
async def test_correction_of_sent_fact_is_explicit_and_replay_preserves_correction_action():
    svc = service()
    paused = svc.pause('c1', 0)
    changed = await svc.submit_input('c1', paused['currentVersion'], '2026-03-15', {'product.purchaseDate': '2026-03-15'})
    await svc.advance('c1', changed['currentVersion'])
    assert svc.exchange.__self__.requests[-1].action == 'correct'
    assert '2026-03-15' in svc.exchange.__self__.requests[-1].data['text']


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
async def test_lost_correction_response_replays_identical_action():
    svc = service()
    paused = svc.pause('c1', 0)
    changed = await svc.submit_input('c1', paused['currentVersion'], '2026-03-15', {'product.purchaseDate': '2026-03-15'})
    original_exchange = svc.exchange
    actions = []
    async def drop_once(request):
        actions.append(request.action)
        if len(actions) == 1: raise TimeoutError('Lost reply')
        return await original_exchange(request)
    svc.exchange = drop_once
    failed = await svc.advance('c1', changed['currentVersion'])
    await svc.advance('c1', failed['currentVersion'])
    assert actions == ['correct', 'correct']


@pytest.mark.asyncio
async def test_new_product_registration_fact_can_be_learned_without_a_question_mapping():
    svc = service('product.details.installation_date')
    pending = await svc.advance('c1', 0)
    assert pending['status'] == 'AWAITING_USER'
    saved = await svc.submit_input('c1', pending['currentVersion'], '2026-03-15')
    assert svc.knowledge.saved[0][1] == {'product.details.installation_date': '2026-03-15'}
    answered = await svc.advance('c1', saved['currentVersion'])
    assert answered['status'] == 'PROCESSING'


def test_preferred_visit_fact_contains_saved_time_not_internal_slot_identifier():
    from app.services.conversation import snapshot_facts
    facts = snapshot_facts({'factsSnapshot': {}, 'preferredDate': '2026-10-20', 'preferredSlotId': 'private-slot',
        'preferredSlot': {'start': '2026-10-20T10:00:00+05:30', 'end': '2026-10-20T12:00:00+05:30'}})
    assert facts['appointment.preference'] == '20 October 2026, 10:00–12:00 IST'
    assert 'private-slot' not in facts['appointment.preference']
