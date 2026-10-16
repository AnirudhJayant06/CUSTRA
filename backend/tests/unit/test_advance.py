import copy
from datetime import datetime, timedelta, timezone

import pytest

from app.services.leases import acquire_lease, check_lease, CaseConflict
from app.services.cases import CaseService
from app.models.exchange import ExchangeResponse, ValidatedAnswer


class RuntimeStore:
    def __init__(self):
        self.case = {"id": "case-1", "currentVersion": 0, "status": "PROCESSING", "stepIndex": 1,
                     "scenarioId": "basic", "businessStage": "product", "eventSequence": 0,
                     "factsSnapshot": {"product": {"brand": "Acme", "model": "Example 1"}},
                     "pendingQuestion": {"question_code": "product", "requested_fields": ["product.brand", "product.model"],
                                         "display_text": "Which product?", "next_stage": "product"}}
        self.operation = {"operationId": "case-1-advance-1"}
        self.messages = []

    def acquire_advance(self, case_id, expected_version):
        self.operation = acquire_lease(self.case, self.operation, expected_version, datetime.now(timezone.utc))
        return {"case": copy.deepcopy(self.case), "operation": copy.deepcopy(self.operation)}

    def save_answer(self, lease, answer):
        check_lease(self.case, self.operation, lease["operation"], datetime.now(timezone.utc))
        self.operation["savedAnswer"] = answer

    def commit_advance(self, lease, changes, events):
        check_lease(self.case, self.operation, lease["operation"], datetime.now(timezone.utc))
        self.case.update(changes)
        self.case["currentVersion"] += 1
        self.case["stepIndex"] += 1
        for event in events:
            if not any(saved["eventId"] == event["eventId"] for saved in self.messages):
                self.messages.append(event)
        self.operation["leaseToken"] = None
        return copy.deepcopy(self.case)

    def fail_advance(self, lease):
        check_lease(self.case, self.operation, lease["operation"], datetime.now(timezone.utc))
        self.case.update(status="ERROR", recoveryPhase="advance")
        self.case["currentVersion"] += 1
        self.operation["leaseToken"] = None
        return copy.deepcopy(self.case)

    def events(self, case_id, after=0):
        return copy.deepcopy(self.messages)


class Consumer:
    def __init__(self, invalid=False): self.calls = 0; self.invalid = invalid
    async def answer(self, question, facts, transcript):
        self.calls += 1
        if self.invalid: raise ValueError("Malformed model output")
        return ValidatedAnswer(text="Brand: Acme; Model: Example 1", field_refs=["product.brand", "product.model"])


class Gateway:
    def __init__(self, drop=False): self.drop = drop; self.operations = []
    async def exchange(self, request):
        self.operations.append(request.operation_id)
        if self.drop:
            self.drop = False
            raise TimeoutError("Response lost after business processed it")
        return ExchangeResponse(question_code="issue", requested_fields=["issue.summary", "issue.description"],
                                display_text="Describe the problem", next_stage="issue", context_id="context-1")


def test_expired_lease_replaced_and_stale_worker_rejected():
    now = datetime.now(timezone.utc)
    case = {"currentVersion": 2, "status": "PROCESSING"}
    previous = {"operationId": "fictional-op", "leaseToken": "old", "expiresAt": (now - timedelta(seconds=1)).isoformat()}
    renewed = acquire_lease(case, previous, 2, now)
    assert renewed["operationId"] == previous["operationId"]
    assert renewed["leaseToken"] != "old"
    with pytest.raises(CaseConflict):
        check_lease(case, renewed, previous, now)
    check_lease(case, renewed, renewed, now)


def test_two_simultaneous_advances_cannot_share_lease():
    now = datetime.now(timezone.utc)
    case = {"currentVersion": 0, "status": "PROCESSING"}
    first = acquire_lease(case, {"operationId": "fictional-op"}, 0, now)
    with pytest.raises(CaseConflict):
        acquire_lease(case, first, 0, now)
    with pytest.raises(CaseConflict):
        acquire_lease(case, {}, 1, now)


def test_stale_version_cannot_commit_even_with_matching_token():
    now = datetime.now(timezone.utc)
    case = {"currentVersion": 0, "status": "PROCESSING"}
    lease = acquire_lease(case, {"operationId": "fictional-op"}, 0, now)
    changed = {**case, "currentVersion": 1}
    with pytest.raises(CaseConflict):
        check_lease(changed, lease, lease, now)


@pytest.mark.asyncio
async def test_lost_response_retry_reuses_answer_and_operation():
    store, consumer, gateway = RuntimeStore(), Consumer(), Gateway(drop=True)
    service = CaseService(None, store, consumer=consumer, gateway=gateway)
    failed = await service.advance("case-1", 0)
    assert failed["status"] == "ERROR"
    assert store.messages == []
    recovered = await service.advance("case-1", failed["currentVersion"])
    assert recovered["status"] == "PROCESSING"
    assert recovered["businessStage"] == "issue"
    assert consumer.calls == 1
    assert gateway.operations == ["case-1-advance-1", "case-1-advance-1"]
    assert len({event["eventId"] for event in store.messages}) == 2


@pytest.mark.asyncio
async def test_invalid_model_output_does_not_advance_or_contact_business():
    store, consumer, gateway = RuntimeStore(), Consumer(invalid=True), Gateway()
    failed = await CaseService(None, store, consumer=consumer, gateway=gateway).advance("case-1", 0)
    assert failed["status"] == "ERROR"
    assert failed["businessStage"] == "product"
    assert gateway.operations == [] and store.messages == []


@pytest.mark.asyncio
async def test_disable_switch_prevents_external_work():
    store, consumer, gateway = RuntimeStore(), Consumer(), Gateway()
    with pytest.raises(CaseConflict):
        await CaseService(None, store, consumer=consumer, gateway=gateway, agent_enabled=False).advance("case-1", 0)
    assert consumer.calls == 0 and gateway.operations == []
