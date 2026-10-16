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


def future_slots() -> list[dict]:
    local = datetime.now(ZoneInfo("Asia/Kolkata"))
    slots = []
    for day in range(1, 4):
        for hour in (9, 15):
            start = (local + timedelta(days=day)).replace(hour=hour, minute=0, second=0, microsecond=0)
            slots.append({"id": f"demo-{start.strftime('%Y%m%d-%H')}",
                          "start": start.astimezone(timezone.utc).isoformat(),
                          "end": (start + timedelta(hours=1)).astimezone(timezone.utc).isoformat(),
                          "timezone": "Asia/Kolkata", "simulated": True})
    return slots


class BusinessService:
    def __init__(self, store):
        self.store = store

    def exchange(self, request: dict, context_id: str) -> dict:
        if request.get("schema_version") != 1 or request.get("scenario_id") != "basic":
            raise ValueError("Unsupported demo scenario")
        for field in ("case_id", "operation_id"):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request.get(field, "")):
                raise ValueError("Invalid exchange identifier")
        digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()

        def generate(state):
            if state and state.get("context_id") != context_id:
                raise ValueError("Business context does not match")
            action, stage = request.get("action"), request.get("stage")
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
            response = await asyncio.to_thread(self.service.exchange, request, context.context_id)
        except (ValueError, KeyError, IndexError) as exc:
            raise InvalidParamsError(message="Invalid simulated business exchange") from exc
        await event_queue.enqueue_event(Message(
            message_id=f"reply-{request['operation_id']}", context_id=response["context_id"],
            role=Role.ROLE_AGENT, parts=[Part(data=ParseDict(response, Value()))],
        ))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None
