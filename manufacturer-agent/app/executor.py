"""Deterministic, clearly simulated business questions over A2A."""

import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.struct_pb2 import Value

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role
from a2a.utils.errors import InvalidParamsError


QUESTIONS = {
    "product": (["product.brand", "product.model"], "What product needs service?", "issue"),
    "issue": (["issue.summary", "issue.description"], "What problem are you seeing?", "contact"),
    "contact": (["profile.name", "profile.phone", "profile.email"], "How can we contact you?", "address"),
    "address": (["address.line1", "address.city", "address.postal_code"], "Where should the visit take place?", "registered"),
}


# Wording variations are business-side fixtures only, never consumer answer hints.
NATURAL_QUESTIONS = [
    ('identity', 'Which appliance and model need servicing?'),
    ('problem', 'What issue should we register?'),
    ('contact', 'How can our service team contact you?'),
    ('location', 'Where should the technician visit?'),
    ('purchase', 'And when did you buy it?'),
]
PURCHASE_VARIANTS = [
    'What date did you purchase this appliance?', 'When was this product bought?',
    'Could you provide its purchase date?', 'And when did you buy it?',
]


from demo_schedule import future_slots


class BusinessService:
    def __init__(self, store):
        self.store = store

    def exchange(self, request: dict, context_id: str) -> dict:
        if request.get("schema_version") != 1 or request.get("scenario_id") not in {"basic", "natural"}:
            raise ValueError("Unsupported demo scenario")
        for field in ("case_id", "operation_id"):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request.get(field, "")):
                raise ValueError("Invalid exchange identifier")
        digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()

        def generate(state):
            if state and state.get("context_id") != context_id:
                raise ValueError("Business context does not match")
            action, stage = request.get("action"), request.get("stage")
            if request.get('scenario_id') == 'natural' and action not in {'book', 'listSlots'}:
                if action == 'start' and stage == 'new' and not state:
                    index = 0
                elif action == 'answer' and state.get('stage') == stage:
                    if not isinstance(request.get('data', {}).get('text'), str) or not request['data']['text'].strip():
                        raise ValueError('A natural-language answer is required')
                    if stage == 'receipt' and not request.get('attachment') and request.get('data', {}).get('deferred') is not True:
                        raise ValueError('Requested invoice was not received')
                    index = state['index'] + 1
                else:
                    raise ValueError('Invalid natural-language exchange')
                updated = {**state, 'index': index, 'context_id': context_id}
                if index < len(NATURAL_QUESTIONS):
                    next_stage, prompt = NATURAL_QUESTIONS[index]
                    if next_stage == 'purchase':
                        prompt = PURCHASE_VARIANTS[int(hashlib.sha256(request['case_id'].encode()).hexdigest()[:2], 16) % 4]
                    response = {'display_text': prompt, 'next_stage': next_stage}
                elif index == len(NATURAL_QUESTIONS) and (state.get('request_document') or request.get('data', {}).get('request_document')):
                    next_stage = 'receipt'
                    response = {'display_text': 'Please send the original invoice.', 'next_stage': next_stage}
                else:
                    next_stage = 'registered'
                    updated.update(reference=f"DEMO-{request['case_id'][:12]}", slots=future_slots())
                    response = {'display_text': 'Simulated complaint registered. Confirm your technician visit.',
                        'next_stage': next_stage, 'reference': updated['reference'], 'slots': updated['slots']}
                updated.update(stage=next_stage, request_document=state.get('request_document', request.get('data', {}).get('request_document', False)))
                response['context_id'] = context_id
                if request.get('attachment'):
                    response['attachment_receipt'] = request['attachment']['version']
                return response, updated
            if action == "listSlots" and state.get("stage") == "registered":
                return {"display_text": "Choose a simulated appointment.", "next_stage": "registered",
                        "reference": state["reference"], "slots": state["slots"], "context_id": context_id}, state
            if action == "book" and stage == "registered" and state.get("stage") in {"registered", "booked"}:
                slot_id = request.get("data", {}).get("slotId")
                existing = state.get("appointment")
                if existing and existing["slotId"] != slot_id:
                    raise ValueError("An appointment is already booked")
                slot = next((item for item in state["slots"] if item["id"] == slot_id), None)
                if not slot or (not existing and datetime.fromisoformat(slot["start"]) <= datetime.now(timezone.utc)):
                    raise ValueError("Appointment slot expired")
                appointment = existing or {
                    "slotId": slot_id, "start": slot["start"], "end": slot["end"],
                    "timezone": slot["timezone"], "simulated": True,
                    "bookingReference": "BOOK-" + hashlib.sha256(f"{request['case_id']}:{slot_id}".encode()).hexdigest()[:12],
                }
                return {"display_text": "Simulated appointment confirmed.", "next_stage": "booked",
                        "reference": state["reference"], "appointment": appointment, "context_id": context_id}, {
                            **state, "stage": "booked", "appointment": appointment}
            if action == "start" and stage == "new" and not state:
                question = "product"
            elif action == "answer" and stage in QUESTIONS and state.get("stage") == stage:
                fields, _, question = QUESTIONS[stage]
                if set(request.get("data", {})) != set(fields) or not all(request["data"].values()):
                    raise ValueError("Missing required answer facts")
            else:
                raise ValueError("Invalid demo action or stage")
            updated = {**state, "stage": question, "context_id": context_id}
            if question == "registered":
                updated.update(reference=f"DEMO-{request['case_id'][:12]}", slots=future_slots())
                response = {"display_text": "Simulated complaint registered. Choose an appointment.",
                            "next_stage": "registered", "reference": updated["reference"], "slots": updated["slots"]}
            else:
                fields, prompt, _ = QUESTIONS[question]
                response = {"question_code": question, "requested_fields": fields,
                            "display_text": prompt, "next_stage": question}
            response["context_id"] = context_id
            return response, updated

        return self.store.transact(request["operation_id"], digest, request["case_id"], generate)


class BusinessExecutor(AgentExecutor):
    def __init__(self, store):
        self.service = BusinessService(store)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        try:
            request = MessageToDict(context.message.parts[0].data)
            attachment = request.get('attachment')
            if attachment:
                raw = context.message.parts[1] if len(context.message.parts) == 2 else None
                if (raw is None or not raw.HasField('raw') or len(raw.raw) > 5_000_000
                        or hashlib.sha256(raw.raw).hexdigest() != attachment.get('version')
                        or raw.media_type != attachment.get('mediaType') or raw.filename != attachment.get('filename')):
                    raise ValueError('Invalid attachment transfer')
            response = await asyncio.to_thread(self.service.exchange, request, context.context_id)
        except (ValueError, KeyError, IndexError) as exc:
            raise InvalidParamsError(message="Invalid simulated business exchange") from exc
        await event_queue.enqueue_event(Message(
            message_id=f"reply-{request['operation_id']}", context_id=response["context_id"],
            role=Role.ROLE_AGENT, parts=[Part(data=ParseDict(response, Value()))],
        ))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None
