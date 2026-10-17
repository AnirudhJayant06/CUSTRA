"""Case snapshots and transactional duplicate protection."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone

from pydantic import ValidationError

from app.models.complaint import ComplaintInput


class IdempotencyConflict(ValueError):
    pass


class CaseValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]):
        self.field_errors = field_errors
        super().__init__("Check the highlighted fields")


class CaseService:
    def __init__(self, vault, store, consumer=None, gateway=None, a2a_url="", agent_enabled=True, a2a_iam_auth=True):
        self.vault = vault
        self.store = store
        self.consumer = consumer
        self.gateway = gateway
        self.a2a_url = a2a_url
        self.agent_enabled = agent_enabled
        self.a2a_iam_auth = a2a_iam_auth

    def create(self, payload: dict, idempotency_key: str) -> dict:
        if not 16 <= len(idempotency_key or "") <= 128:
            raise CaseValidationError({"idempotencyKey": "A stable request key is required"})
        try:
            data = ComplaintInput.model_validate(payload).model_dump(mode="json", exclude_none=True)
        except ValidationError as exc:
            raise CaseValidationError({str(item["loc"][-1]): item["msg"] for item in exc.errors()}) from exc

        digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        replay = self.store.replay_creation(idempotency_key, digest)
        if replay is not None:
            return replay

        if data.get('preferredSlotId'):
            from app.services.demo_schedule import demo_schedule
            preference = next((slot for slot in demo_schedule() if slot['id'] == data['preferredSlotId']
                               and slot['date'] == data['preferredDate'] and slot['available']), None)
            if not preference:
                raise CaseValidationError({'preferredSlotId': 'This preferred time is unavailable; choose another'})

        profile = self.vault.get_profile()
        missing = {field: "Complete this in Account settings" for field in ("name", "phone", "email")
                   if not str(profile.get(field) or "").strip()}
        if missing:
            raise CaseValidationError(missing)
        if hasattr(self.vault, "seed_demo_address"):
            self.vault.seed_demo_address()
        try:
            product = self.vault.get_product(data["productId"])
            address = self.vault.get_address(data["addressId"])
        except LookupError as exc:
            raise CaseValidationError({"productId": "Choose a saved product and address",
                                       "addressId": "Choose a saved product and address"}) from exc

        catalog = self.vault.catalog() if hasattr(self.vault, "catalog") else {"categories": []}
        category = next((x for x in catalog["categories"] if x["id"] == product.get("categoryId")), None)
        brand = next((x for x in category["brands"] if x["id"] == product.get("brandId")), None) if category else None
        facts = {
            "profile": copy.deepcopy(profile),
            "product": {**copy.deepcopy(product), "brand": brand["name"] if brand else product.get("brandId"),
                        "model": product.get("modelNumber") or (product.get("displayName") if "modelNumber" not in product else f"{category['name'] if category else product.get('categoryId')} (model not recorded)")},
            "address": {**copy.deepcopy(address), "postal_code": address.get("postalCode")},
            "issue": {"summary": data["issueSummary"], "description": data["description"]},
        }
        record = {
            "id": uuid.uuid4().hex, **data, "factsSnapshot": facts,
            "status": "PROCESSING", "businessStage": "new", "currentVersion": 0,
            "scenarioId": "basic", "reference": None,
            "stepIndex": 0, "eventSequence": 0,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        return self.store.create_if_absent(idempotency_key, digest, record)

    def get(self, case_id: str) -> dict:
        record = self.store.get(case_id)
        if record is None:
            raise LookupError("Complaint not found")
        return record

    def list(self, product_id: str | None = None) -> list[dict]:
        return self.store.list(product_id)

    async def _exchange(self, request):
        if self.gateway:
            return await self.gateway.exchange(request)
        import httpx
        from app.services.a2a_gateway import A2AGateway, CloudRunAuth

        if not self.a2a_url:
            raise ValueError("Business service is not configured")
        async with httpx.AsyncClient(timeout=8, auth=CloudRunAuth(self.a2a_url) if self.a2a_iam_auth else None) as client:
            return await A2AGateway(self.a2a_url, client).exchange(request)

    async def advance(self, case_id: str, expected_version: int) -> dict:
        from app.agents.consumer import validate_answer
        from app.models.exchange import ExchangeRequest, ExchangeResponse
        from app.services.leases import CaseConflict

        if not self.agent_enabled:
            raise CaseConflict("Agent processing is disabled")
        lease = None
        try:
            async with asyncio.timeout(40):
                lease = await asyncio.to_thread(self.store.acquire_advance, case_id, expected_version)
                case, operation = lease["case"], lease["operation"]
                stage = case["businessStage"]
                if case.get("stepIndex", 0) > 4:
                    raise ValueError("Question limit reached")
                answer = None
                data = {}
                if stage != "new":
                    question = ExchangeResponse.model_validate(case["pendingQuestion"])
                    if question.requested_fields != QUESTION_FIELDS.get(stage):
                        raise ValueError("Unsupported business question")
                    saved = operation.get("savedAnswer")
                    if saved:
                        answer = validate_answer(saved, question, case["factsSnapshot"])
                    else:
                        if self.consumer is None:
                            raise ValueError("Consumer Agent is not configured")
                        transcript = await asyncio.to_thread(self.store.events, case_id)
                        answer = await self.consumer.answer(question, case["factsSnapshot"], transcript)
                        answer = validate_answer(answer.model_dump(), question, case["factsSnapshot"])
                        await asyncio.to_thread(self.store.save_answer, lease, answer.model_dump())
                    for field in question.requested_fields:
                        section, name = field.split(".")
                        data[field] = case["factsSnapshot"][section][name]
                response = await self._exchange(ExchangeRequest(
                    schema_version=1, case_id=case_id, operation_id=operation["operationId"],
                    scenario_id=case["scenarioId"], action="start" if stage == "new" else "answer",
                    stage=stage, data=data, context_id=case.get("protocolContextId"),
                ))
                expected = NEXT_STAGE.get(stage)
                if response.next_stage != expected:
                    raise ValueError("Business returned an unexpected stage")
                if case.get("protocolContextId") and response.context_id != case["protocolContextId"]:
                    raise ValueError("Business context changed")
                if expected != "registered" and response.requested_fields != QUESTION_FIELDS[expected]:
                    raise ValueError("Business requested unsupported facts")
                if expected == "registered" and (not response.reference or not response.slots):
                    raise ValueError("Business registration lacks reference or slots")
                if expected == "registered" and any(slot.start <= datetime.now(timezone.utc) for slot in response.slots):
                    raise ValueError("Business offered an expired appointment")
                events = []
                sequence = case.get("eventSequence", 0)
                if answer:
                    sequence += 1
                    events.append({"eventId": f"{operation['operationId']}-consumer", "sequence": sequence,
                                   "role": "consumer", "displayText": answer.text, "simulated": False})
                sequence += 1
                events.append({"eventId": f"{operation['operationId']}-business", "sequence": sequence,
                               "role": "business", "displayText": response.display_text, "simulated": True})
                changes = {
                    "businessStage": response.next_stage, "pendingQuestion": response.model_dump(mode="json"),
                    "protocolContextId": response.context_id,
                    "protocolMessageId": response.message_id, "protocolTaskId": response.task_id,
                    "eventSequence": sequence, "reference": response.reference or case.get("reference"),
                    "status": "AWAITING_APPOINTMENT" if expected == "registered" else "PROCESSING",
                    "slots": response.model_dump(mode="json")["slots"], "recoveryPhase": None, "error": None,
                }
                return await asyncio.to_thread(self.store.commit_advance, lease, changes, events)
        except CaseConflict:
            raise
        except Exception:
            if lease:
                return await asyncio.to_thread(self.store.fail_advance, lease)
            raise

    def slots(self, case_id: str) -> list[dict]:
        from app.models.exchange import AppointmentSlot
        from app.services.leases import CaseConflict

        case = self.get(case_id)
        if case["status"] not in {"AWAITING_APPOINTMENT", "ERROR"}:
            raise CaseConflict("This case is not awaiting an appointment")
        return [slot for slot in case.get("slots", [])
                if AppointmentSlot.model_validate(slot).start > datetime.now(timezone.utc)
                or (case.get("recoveryPhase") == "book" and case.get("pendingSlotId") == slot["id"])]

    async def book(self, case_id: str, slot_id: str, idempotency_key: str) -> dict:
        from app.models.exchange import AppointmentSlot, ExchangeRequest
        from app.services.leases import CaseConflict

        if not self.agent_enabled:
            raise CaseConflict("Agent processing is disabled")
        if not 16 <= len(idempotency_key or "") <= 128:
            raise CaseConflict("A stable booking request key is required")
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        lease = None
        try:
            async with asyncio.timeout(40):
                case = await asyncio.to_thread(self.get, case_id)
                if case["status"] == "BOOKED":
                    if case["appointment"]["slotId"] == slot_id:
                        return case
                    raise CaseConflict("This case already has a confirmed appointment")
                choices = await asyncio.to_thread(self.slots, case_id)
                selected = next((slot for slot in choices if slot["id"] == slot_id), None)
                if selected is None:
                    raise CaseConflict("This slot is no longer available; choose another")
                lease = await asyncio.to_thread(self.store.acquire_booking, case_id, case["currentVersion"], slot_id, key_hash)
                response = await self._exchange(ExchangeRequest(
                    schema_version=1, case_id=case_id, operation_id=lease["operation"]["operationId"],
                    scenario_id=case["scenarioId"], action="book", stage="registered", data={"slotId": slot_id},
                    context_id=case.get("protocolContextId"),
                ))
                appointment = response.appointment
                slot = AppointmentSlot.model_validate(selected)
                if (response.next_stage != "booked" or not appointment
                        or response.context_id != case.get("protocolContextId")
                        or appointment.slotId != slot_id or appointment.start != slot.start
                        or appointment.end != slot.end):
                    raise ValueError("Invalid business booking confirmation")
                return await asyncio.to_thread(self.store.commit_booking, lease, appointment.model_dump(mode="json"))
        except CaseConflict:
            raise
        except Exception:
            if lease:
                return await asyncio.to_thread(self.store.fail_booking, lease)
            raise

    def confirm_resolution(self, case_id: str, confirmed: bool) -> dict:
        from app.services.leases import CaseConflict

        case = self.get(case_id)
        if confirmed is not True or case["status"] not in {"BOOKED", "CLOSED"}:
            raise CaseConflict("Confirm resolution only after your booked service is complete")
        if case["status"] == "CLOSED":
            return case
        return self.store.close_case(case_id)


QUESTION_FIELDS = {
    "product": ["product.brand", "product.model"],
    "issue": ["issue.summary", "issue.description"],
    "contact": ["profile.name", "profile.phone", "profile.email"],
    "address": ["address.line1", "address.city", "address.postal_code"],
}
NEXT_STAGE = {"new": "product", "product": "issue", "issue": "contact", "contact": "address", "address": "registered"}
