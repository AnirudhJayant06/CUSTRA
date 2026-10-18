"""Natural-language turns with durable handoff and existing operation leases."""
import copy
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.models.exchange import ExchangeRequest, ExchangeResponse
from app.models.knowledge import PRODUCT_FIELDS, CONTEXT_FIELDS, Resolution, GroundedAnswer, is_fact_field, is_product_field
from app.agents.knowledge import validate_resolution, validate_grounding
from app.services.leases import CaseConflict
from app.services.knowledge import passage_is_certain


def snapshot_facts(case):
    result = {}
    for section, values in case['factsSnapshot'].items():
        for name, value in values.items():
            field = f'{section}.{name}'
            if is_fact_field(field) and value not in (None, ''):
                result[field] = str(value)
    if case.get('preferredDate'):
        slot = case.get('preferredSlot')
        if slot:
            start = datetime.fromisoformat(slot['start']).astimezone(ZoneInfo('Asia/Kolkata'))
            end = datetime.fromisoformat(slot['end']).astimezone(ZoneInfo('Asia/Kolkata'))
            result['appointment.preference'] = start.strftime('%d %B %Y, %H:%M') + '–' + end.strftime('%H:%M') + ' IST'
        else:
            result['appointment.preference'] = case['preferredDate'] + ' (time must be confirmed)'
    return result


class ConversationService:
    def __init__(self, store, knowledge, model, exchange):
        self.store, self.knowledge, self.model, self.exchange = store, knowledge, model, exchange

    def _events(self, case, operation, messages):
        return [{'eventId': f"{operation['operationId']}-{i}", 'sequence': case.get('eventSequence', 0)+i+1,
                 'role': role, 'displayText': text, 'simulated': role == 'business'}
                for i, (role, text) in enumerate(messages)]

    async def _handoff(self, lease, prompt, fields, kind='fact', **extra):
        case, operation = lease['case'], lease['operation']
        events = self._events(case, operation, [('system', prompt)])
        return await asyncio.to_thread(self.store.commit_advance, lease, {'status': 'AWAITING_USER',
            'pendingUserRequest': {'kind': kind, 'prompt': prompt, 'fields': fields, **extra},
            'eventSequence': events[-1]['sequence'], 'error': None, 'recoveryPhase': None}, events)

    async def _attempt(self, lease, role, call, deadline):
        """At most three persisted preparation attempts per role and turn."""
        preparation = lease['operation'].setdefault('preparation', {})
        attempts = preparation.setdefault('attempts', {})
        while attempts.get(role, 0) < 3:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return None
            attempts[role] = attempts.get(role, 0) + 1
            await asyncio.to_thread(self.store.save_preparation, lease, preparation)
            try:
                async with asyncio.timeout(min(10, remaining)):
                    return await call()
            except CaseConflict:
                raise
            except Exception:
                # No facts or private model output in errors; use grounded fallback.
                continue
        return None

    def _fallback(self, case, fields=(), facts=None, reason='unresolved'):
        facts = facts or {}
        known = {field: str(facts[field]) for field in fields if field in facts}
        missing = [field for field in fields if field not in known]
        deferred = bool(missing or not fields)
        text = '; '.join(known.values())
        if deferred:
            text = (text + '. ' if text else '') + 'The technician will confirm this detail during the visit.'
        return {'action': 'answer', 'text': text, 'attachment': None,
            'data': {'text': text, 'values': known, 'citations': [f'fact:{k}' for k in known],
                     'deferred': deferred, 'deferredFields': missing},
            'artifact': {'originalQuestion': case['pendingQuestion']['display_text'],
                         'fallbackReason': reason, 'answer': text}}

    async def _prepare(self, lease):
        case, operation = lease['case'], lease['operation']
        if case['businessStage'] == 'new':
            return {'action': 'start', 'data': {}, 'text': None, 'artifact': None}
        if case.get('deferQuestion'):
            return self._fallback(case, reason='customer_continued_without_detail')
        deadline = asyncio.get_running_loop().time() + 30
        original = case['pendingQuestion']['display_text']
        preparation = operation.setdefault('preparation', {})
        resolution = preparation.get('resolution')
        if not resolution:
            history = (await asyncio.to_thread(self.store.events, case['id']))[-12:]
            async def resolve():
                return validate_resolution(Resolution.model_validate(await self.model.resolve(original, {
                    **case['factsSnapshot'], 'history': history, 'clarification': case.get('userClarification')})))
            resolved = await self._attempt(lease, 'resolve', resolve, deadline)
            if resolved is None:
                return self._fallback(case, reason='resolution_unavailable')
            resolution = resolved.model_dump()
            preparation['resolution'] = resolution
            await asyncio.to_thread(self.store.save_preparation, lease, preparation)
        resolution = Resolution.model_validate(resolution)
        if resolution.needs_clarification:
            return self._fallback(case, resolution.requested_facts, reason='ambiguous_question')
        consent = case.get('sharingConsent') if resolution.requires_document else None
        if resolution.requires_document and not consent:
            try:
                candidates = [d for d in await asyncio.to_thread(self.knowledge.documents, case['productId'])
                    if d.get('documentType') == resolution.document_type and d.get('processingStatus') == 'searchable']
            except Exception:
                candidates = []
            return {'handoff': await self._handoff(lease,
                'The business requested a document. Share it or continue for the technician to review it during the visit.', [],
                'share', candidates=candidates)}
        fields = resolution.requested_facts
        facts = snapshot_facts(case)
        knowledge = {'facts': {}, 'conflicts': {}, 'revision': 0}
        # Contact and address answers must not depend on product-document services.
        if any(is_product_field(field) for field in fields):
            try:
                knowledge = await asyncio.to_thread(self.knowledge.get, case['productId'])
            except Exception:
                pass
            facts.update({k: str(v['value']) for k, v in knowledge['facts'].items() if is_product_field(k)})
        facts.update(case.get('factOverrides', {}))
        conflicts = (set(knowledge.get('conflicts', {})) & set(fields)) - set(case.get('factOverrides', {}))
        for field in conflicts:
            facts.pop(field, None)
        evidence = [{'id': f'fact:{key}', 'field': key, 'value': facts[key], 'text': facts[key],
            'revision': knowledge['revision'],
            'source': case.get('factOverrideSources', {}).get(key) or knowledge['facts'].get(key, {}).get('source') or
                      {'type': 'complaint_snapshot', 'id': case['id']}}
            for key in fields if key in facts]
        missing = [key for key in fields if key not in facts]
        evidence.extend(case.get('chatEvidence') or [])
        if missing and not conflicts:
            found = await self._attempt(lease, 'search',
                lambda: self.knowledge.search(case['productId'], resolution.standalone_question), deadline)
            evidence.extend(found or [])
        answer = None
        if evidence and not conflicts:
            async def compose():
                return validate_grounding(GroundedAnswer.model_validate(
                    await self.model.compose(resolution.standalone_question, evidence)), evidence)
            answer = await self._attempt(lease, 'compose', compose, deadline)
        if consent and not fields:
            text = 'The customer shared the requested document.'
            payload = {'action': 'answer', 'text': text, 'data': {'text': text},
                'artifact': {'originalQuestion': original, 'answer': text}}
        elif answer is None or answer.missing or conflicts:
            payload = self._fallback(case, fields, facts, 'answer_or_evidence_unavailable')
        else:
            payload = {'action': 'answer', 'text': answer.text,
                'data': {'text': answer.text, 'values': answer.values, 'citations': answer.citations},
                'artifact': {'originalQuestion': original, 'resolvedQuestion': resolution.model_dump(),
                    'evidence': evidence, 'knowledgeRevision': knowledge['revision'], 'answer': answer.text}}
        if consent:
            payload['attachment'] = consent
        payload['artifact'].update(resolvedQuestion=resolution.model_dump(),
            evidence=evidence, knowledgeRevision=knowledge['revision'])
        return payload

    async def advance(self, case_id, expected_version):
        # Compatibility only: release cases left in the removed pause UI.
        previous = await asyncio.to_thread(self.store.get, case_id)
        if previous and previous['status'] == 'PAUSED':
            previous = await asyncio.to_thread(self.store.interact, case_id, expected_version,
                {'status': 'PROCESSING', 'pausedStatus': None, 'queuedCorrection': None})
            expected_version = previous['currentVersion']
        lease = await asyncio.to_thread(self.store.acquire_advance, case_id, expected_version)
        case, operation = lease['case'], lease['operation']
        try:
            async with asyncio.timeout(45):
                if case.get('stepIndex', 0) >= 30:
                    return await self._handoff(lease, 'This conversation needs your assistance to continue.', [], 'clarification')
                stage = case['businessStage']
                messages = []; payload = operation.get('savedAnswer')
                if not payload:
                    try:
                        async with asyncio.timeout(32):
                            payload = await self._prepare(lease)
                    except TimeoutError:
                        payload = self._fallback(case, reason='preparation_deadline')
                    if 'handoff' in payload:
                        return payload['handoff']
                    await asyncio.to_thread(self.store.save_answer, lease, payload)
                # Consent/customer input during preparation invalidates stale drafts.
                latest = await asyncio.to_thread(self.store.get, case_id)
                if latest['currentVersion'] != case['currentVersion'] or latest['status'] not in {'PROCESSING', 'ERROR'}:
                    raise CaseConflict('Conversation changed; resume from saved progress')
                request = ExchangeRequest(schema_version=1, case_id=case_id, operation_id=operation['operationId'],
                    scenario_id='natural', action=payload['action'], stage=stage,
                    data=payload['data'], context_id=case.get('protocolContextId'), attachment=payload.get('attachment'))
                if hasattr(self.store, "mark_send"):
                    await asyncio.to_thread(self.store.mark_send, lease)
                response = await self.exchange(request)
                if payload.get('attachment') and response.attachment_receipt != payload['attachment']['version']:
                    raise ValueError('Business did not acknowledge the shared document')
                if case.get('protocolContextId') and response.context_id != case['protocolContextId']:
                    raise ValueError('Business context changed')
                if response.next_stage == 'registered' and (not response.reference or not response.slots or
                    any(slot.start <= datetime.now(timezone.utc) for slot in response.slots)):
                    raise ValueError('Invalid registration result')
                if hasattr(self.store, 'save_external_result'):
                    await asyncio.to_thread(self.store.save_external_result, operation['operationId'], response.model_dump(mode='json'))
                if payload['artifact'] and hasattr(self.knowledge, 'records'):
                    try:
                        await asyncio.to_thread(self.knowledge.records.mutate, 'turns', operation['operationId'], lambda _: payload['artifact'])
                    except Exception:
                        pass  # Optional retrieval audit storage cannot block an acknowledged turn.
                if payload['text']:
                    messages.append(('consumer', payload['text']))
                messages.append(('business', response.display_text))
                events = self._events(case, operation, messages)
                return await asyncio.to_thread(self.store.commit_advance, lease, {
                    'status': 'AWAITING_APPOINTMENT' if response.next_stage == 'registered' else 'PROCESSING',
                    'businessStage': response.next_stage, 'pendingQuestion': response.model_dump(mode='json'),
                    'protocolContextId': response.context_id, 'protocolMessageId': response.message_id,
                    'protocolTaskId': response.task_id, 'reference': response.reference or case.get('reference'),
                    'slots': [s.model_dump(mode='json') for s in response.slots], 'pendingUserRequest': None,
                    'deferQuestion': None,
                    'deferredQuestions': case.get('deferredQuestions', []) + ([{
                        'question': case['pendingQuestion']['display_text'], 'fields': payload['data'].get('deferredFields', []),
                        'operationId': operation['operationId']}] if payload['data'].get('deferred') else []),
                    'sharingConsent': None, 'chatEvidence': None, 'userClarification': None,
                    'eventSequence': events[-1]['sequence'], 'recoveryPhase': None, 'error': None}, events)
        except CaseConflict:
            raise
        except Exception:
            return await asyncio.to_thread(self.store.fail_advance, lease)

    async def submit_input(self, case_id, version, text, values=None, document_id=None):
        case = await asyncio.to_thread(self.store.get, case_id)
        if not case or case['currentVersion'] != version:
            raise CaseConflict('Complaint changed; reload before replying')
        if case['status'] != 'AWAITING_USER':
            raise CaseConflict('This conversation is not waiting for input')
        pending = case.get('pendingUserRequest') or {}
        fields = pending.get('fields', [])
        values = dict(values or {})
        if text and len(fields) == 1 and not values:
            values[fields[0]] = text.strip()
        snapshot = copy.deepcopy(case['factsSnapshot']); overrides = dict(case.get('factOverrides', {}))
        override_sources = dict(case.get('factOverrideSources', {}))
        if not all(is_fact_field(field) for field in values):
            raise ValueError('Unsupported fact')
        if set(values) - set(fields):
            raise ValueError('Only the detail requested by the business can be supplied')
        if case['status'] == 'AWAITING_USER' and not document_id and pending.get('kind') == 'fact' and set(fields) - values.keys():
            raise ValueError('Provide each requested fact')
        for field, value in values.items():
            if not isinstance(value, str) or not value.strip() or len(value) > 500:
                raise ValueError('Enter a valid fact')
            overrides[field] = value.strip()
            override_sources[field] = {'type': 'user', 'id': f'{case_id}-input-{version}'}
            section, name = field.split('.', 1)
            snapshot.setdefault(section, {})[name] = value.strip()
        changes = {'factsSnapshot': snapshot, 'factOverrides': overrides, 'factOverrideSources': override_sources, 'status': 'PROCESSING',
            'pendingUserRequest': None, 'userClarification': text if not values else None, 'error': None, 'recoveryPhase': None}
        extracted_reusable = {}
        if document_id:
            result = await self.knowledge.inspect_chat(case, document_id, case['pendingQuestion']['display_text'])
            if not result['product_match']:
                raise ValueError('This attachment could not be matched to the product')
            changes['chatEvidence'] = [{'id': f'chat:{document_id}:{i}', 'text': p['text'], 'documentId': document_id,
                'page': p['page']} for i, p in enumerate(result['passages'])
                if passage_is_certain(p, result['facts'], result['passages'])]
            if not changes['chatEvidence']:
                raise ValueError('No readable supporting evidence; enter the detail instead')
            changes['suggestedProductDocument'] = document_id if result['document_type'] in {'invoice', 'warranty', 'serial_label'} else None
            for fact in result['facts']:
                if (is_product_field(fact['field']) and not fact['uncertain']
                    and any(fact['page'] == p['page'] and fact['quote'] in p['text'] for p in result['passages'])):
                    extracted_reusable[fact['field']] = fact['value']
        saved = await asyncio.to_thread(self.store.interact, case_id, version, changes, text or ('Document supplied' if document_id else 'Details updated'))
        reusable = {k: v for k, v in values.items() if is_product_field(k)}
        if reusable:
            await asyncio.to_thread(self.knowledge.merge_facts, case['productId'], reusable,
                {'type': 'user', 'id': f"{case_id}-input-{version}"}, correction=True)
        if extracted_reusable:
            await asyncio.to_thread(self.knowledge.merge_facts, case['productId'], extracted_reusable,
                {'type': 'document', 'id': document_id, 'caseId': case_id}, correction=False)
        return saved

    def continue_without_detail(self, case_id, version):
        case = self.store.get(case_id)
        if not case or case['status'] != 'AWAITING_USER':
            raise CaseConflict('This conversation is not awaiting a detail')
        return self.store.interact(case_id, version, {'status': 'PROCESSING',
            'pendingUserRequest': None, 'deferQuestion': True},
            'Continue; the technician will confirm this detail during the visit.')

    def share(self, case_id, version, document_id, document_version):
        import hashlib
        case = self.store.get(case_id)
        if not case:
            raise CaseConflict('Complaint not found')
        if case['status'] != 'AWAITING_USER' or (case.get('pendingUserRequest') or {}).get('kind') != 'share':
            raise CaseConflict('This conversation is not awaiting file-sharing consent')
        self.knowledge._source(case['productId'], document_id, case['id'])
        metadata, stream = self.knowledge.files.open(document_id)
        with stream:
            content = stream.read(5_000_001)
        if hashlib.sha256(content).hexdigest() != document_version:
            raise CaseConflict('Document changed; review the file before sharing')
        consent = {'documentId': document_id, 'version': document_version,
                   'filename': metadata['originalName'], 'mediaType': metadata['mediaType']}
        return self.store.interact(case_id, version, {'status': 'PROCESSING', 'pendingUserRequest': None,
            'sharingConsent': consent}, 'Share document: ' + metadata['originalName'])
