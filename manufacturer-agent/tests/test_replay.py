import copy
import threading
from datetime import datetime, timedelta, timezone

import pytest

from executor import BusinessService


class MemoryReplayStore:
    def __init__(self):
        self.operations = {}
        self.cases = {}
        self.lock = threading.Lock()

    def transact(self, operation_id, digest, case_id, generate):
        with self.lock:
            if operation_id in self.operations:
                previous_digest, response = self.operations[operation_id]
                if previous_digest != digest: raise ValueError("Operation payload changed")
                return copy.deepcopy(response)
            response, state = generate(copy.deepcopy(self.cases.get(case_id, {})))
            self.cases[case_id] = state
            self.operations[operation_id] = (digest, copy.deepcopy(response))
            return copy.deepcopy(response)


def request(action="start", stage="new", operation="op-start", data=None):
    return {"schema_version": 1, "case_id": "fictional-case", "operation_id": operation,
            "scenario_id": "basic", "action": action, "stage": stage, "data": data or {}}


def test_lost_response_replays_across_service_restart():
    store = MemoryReplayStore()
    first = BusinessService(store).exchange(request(), "context-1")
    replay = BusinessService(store).exchange(request(), "new-transport-context")
    assert replay == first
    assert replay["context_id"] == "context-1"
    assert len(store.operations) == 1


def test_four_supported_questions_register_once_and_offer_future_slots():
    store = MemoryReplayStore()
    business = BusinessService(store)
    response = business.exchange(request(), "context-1")
    facts = {
        "product.brand": "Acme", "product.model": "Example", "issue.summary": "Leak",
        "issue.description": "Fictional leak", "profile.name": "Fictional User",
        "profile.phone": "9999999999", "profile.email": "fictional@example.test",
        "address.line1": "1 Fiction Lane", "address.city": "Pune", "address.postal_code": "411001",
    }
    for index in range(4):
        stage = response["next_stage"]
        payload = request("answer", stage, f"op-{index}",
                          {field: facts[field] for field in response["requested_fields"]})
        response = business.exchange(payload, "context-1")
    assert response["reference"].startswith("DEMO-")
    assert response["next_stage"] == "registered"
    assert len(response["slots"]) == 6
    assert BusinessService(store).exchange(payload, "context-1") == response


def test_unknown_scenario_or_context_never_registers():
    store = MemoryReplayStore()
    business = BusinessService(store)
    with pytest.raises(ValueError):
        business.exchange({**request(), "scenario_id": "unsupported"}, "context-1")
    response = business.exchange(request(), "context-1")
    with pytest.raises(ValueError):
        business.exchange(request("answer", "product", "op-answer", {
            "product.brand": "Acme", "product.model": "Example"}), "wrong-context")


def registered_business():
    store = MemoryReplayStore()
    service = BusinessService(store)
    response = service.exchange(request(), "context-1")
    for index in range(4):
        response = service.exchange(request("answer", response["next_stage"], f"answer-{index}",
                                            {field: "Fictional" for field in response["requested_fields"]}), "context-1")
    return store, service, response


def test_booking_replay_is_stable_after_lost_response():
    store, service, response = registered_business()
    slot_id = response["slots"][0]["id"]
    payload = request("book", "registered", "book-stable", {"slotId": slot_id})
    booked = service.exchange(payload, "context-1")
    assert BusinessService(store).exchange(payload, "context-1") == booked
    assert booked["appointment"]["slotId"] == slot_id
    assert booked["appointment"]["simulated"] is True
    with pytest.raises(ValueError):
        service.exchange(request("book", "registered", "book-other", {"slotId": response["slots"][1]["id"]}), "context-1")


def test_stale_business_slot_cannot_book():
    store, service, response = registered_business()
    store.cases["fictional-case"]["slots"][0]["start"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with pytest.raises(ValueError):
        service.exchange(request("book", "registered", "book-stale", {"slotId": response["slots"][0]["id"]}), "context-1")
