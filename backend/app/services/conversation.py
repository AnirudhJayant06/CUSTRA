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

    async def advance(self, case_id, expected_version):
        lease = await asyncio.to_thread(self.store.acquire_advance, case_id, expected_version)
        case, operation = lease['case'], lease['operation']
        try:
            async with asyncio.timeout(45):
                if case.get('stepIndex', 0) >= 30:
                    return await self._handoff(lease, 'This conversation needs your assistance to continue.', [], 'clarification')
                stage = case['businessStage']
                correcting = bool(case.get('queuedCorrection')) and not operation.get('savedAnswer')
                messages = []; payload = operation.get('savedAnswer')
                if not payload:
                    payload = {'data': {}, 'text': None, 'artifact': None}
                    if correcting:
                        payload.update(text='Correction from the customer: ' + case['queuedCorrection'],
                                       data={'text': 'Correction from the customer: ' + case['queuedCorrection']})
                    elif stage != 'new':
                        original = case['pendingQuestion']['display_text']
                        history = (await asyncio.to_thread(self.store.events, case_id))[-12:]
                        resolution = validate_resolution(Resolution.model_validate(await self.model.resolve(original, {
                            'product': case['factsSnapshot'].get('product'), 'history': history,
                            'clarification': case.get('userClarification'), 'issue': case['factsSnapshot'].get('issue')})))
                        if resolution.needs_clarification:
                            return await self._handoff(lease, resolution.clarification or 'Please clarify the business question.', [], 'clarification')
                        if resolution.requires_document:
                            consent = case.get('sharingConsent')
                            if not consent:
                                candidates = [d for d in await asyncio.to_thread(self.knowledge.documents, case['productId'])
                                    if d.get('documentType') == resolution.document_type and d.get('processingStatus') == 'searchable']
                                return await self._handoff(lease, 'The business requested a document. Choose the file to share.', [],
                                    'share', candidates=candidates)
                            payload['attachment'] = consent
                        facts = snapshot_facts(case)
                        knowledge = await asyncio.to_thread(self.knowledge.get, case['productId'])
                        facts.update({k: v['value'] for k, v in knowledge['facts'].items()})
                        # Explicit complaint corrections override older product knowledge.
                        facts.update(case.get('factOverrides', {}))
                        conflicts = set(knowledge.get('conflicts', {})) & set(resolution.requested_facts)
                        if conflicts:
                            return await self._handoff(lease, 'Please confirm the conflicting product information.', sorted(conflicts))
                        evidence = [{'id': f'fact:{k}', 'field': k, 'value': facts[k], 'text': facts[k],
                                     'revision': knowledge['revision']} for k in resolution.requested_facts if k in facts]
                        for item in evidence:
                            key = item['field']
                            if key in case.get('factOverrides', {}):
                                item['source'] = case.get('factOverrideSources', {}).get(key, {'type': 'user', 'id': case_id})
                            else:
                                item['source'] = knowledge['facts'].get(key, {}).get('source', {'type': 'complaint_snapshot', 'id': case_id})
                        missing = [k for k in resolution.requested_facts if k not in facts]
                        if case.get('chatEvidence'):
                            evidence.extend(case['chatEvidence'])
                        if missing:
                            try:
                                evidence.extend(await self.knowledge.search(case['productId'], resolution.standalone_question))
                            except Exception:
                                return await self._handoff(lease, 'Document search is unavailable. Please supply the requested detail.', missing)
                        if not evidence and not payload.get('attachment'):
                            return await self._handoff(lease, original, missing or resolution.requested_facts)
                        if evidence:
                            answer = validate_grounding(GroundedAnswer.model_validate(
                                await self.model.compose(resolution.standalone_question, evidence)), evidence)
                            if answer.missing:
                                return await self._handoff(lease, answer.text, missing or resolution.requested_facts)
                            payload.update(text=answer.text, data={'text': answer.text, 'values': answer.values,
                                'citations': answer.citations})
                        else:
                            payload.update(text='The customer shared the requested document.', data={'text': 'Requested document attached.'})
                        payload['artifact'] = {'originalQuestion': original, 'resolvedQuestion': resolution.model_dump(),
                            'evidence': evidence, 'knowledgeRevision': knowledge['revision'], 'answer': payload['text']}
                    payload['action'] = 'correct' if correcting else ('start' if stage == 'new' else 'answer')
                    await asyncio.to_thread(self.store.save_answer, lease, payload)
                # A pause/correction during a model call prevents subsequent send.
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
                    await asyncio.to_thread(self.knowledge.records.mutate, 'turns', operation['operationId'], lambda _: payload['artifact'])
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
                    'queuedCorrection': None if payload['action'] == 'correct' else case.get('queuedCorrection'),
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
        if case['status'] not in {'AWAITING_USER', 'PAUSED'}:
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
        if case['status'] == 'PAUSED' and values and case['businessStage'] != 'new':
            import re
            changes['queuedCorrection'] = '; '.join(
                re.sub(r'(?<!^)(?=[A-Z])', ' ', key.rsplit('.', 1)[-1]).replace('_', ' ').capitalize() + ': ' + value
                for key, value in values.items())
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

    def pause(self, case_id, version):
        case = self.store.get(case_id)
        if not case:
            raise CaseConflict('Complaint not found')
        if case['status'] not in {'PROCESSING', 'ERROR', 'AWAITING_USER'}:
            raise CaseConflict('This conversation cannot be paused now')
        return self.store.interact(case_id, version, {'status': 'PAUSED', 'pausedStatus': case['status']})

    def resume(self, case_id, version):
        case = self.store.get(case_id)
        if not case:
            raise CaseConflict('Complaint not found')
        if case['status'] != 'PAUSED':
            raise CaseConflict('This conversation is not paused')
        status = case.get('pausedStatus', 'PROCESSING')
        return self.store.interact(case_id, version, {'status': status, 'pausedStatus': None})

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
