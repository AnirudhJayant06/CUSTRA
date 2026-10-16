import copy
from datetime import datetime, timedelta, timezone

import pytest

from app.models.exchange import ExchangeResponse
from app.services.cases import CaseService
from app.services.leases import CaseConflict, acquire_lease, check_lease


class BookingStore:
    def __init__(self):
        start = datetime.now(timezone.utc) + timedelta(days=1)
        self.slot = {"id": "slot-1", "start": start.isoformat(), "end": (start + timedelta(hours=1)).isoformat(),
                     "timezone": "Asia/Kolkata", "simulated": True}
        self.case = {"id": "case-1", "status": "AWAITING_APPOINTMENT", "businessStage": "registered",
                     "currentVersion": 5, "scenarioId": "basic", "slots": [self.slot],
                     "protocolContextId": "context-1", "reference": "DEMO-1", "eventSequence": 9}
        self.operation = None

    def get(self, id): return copy.deepcopy(self.case)

    def acquire_booking(self, case_id, version, slot_id, key_hash):
        if self.operation and self.operation["slotId"] != slot_id:
            raise CaseConflict("Booking is already pending")
        previous = self.operation or {"operationId": "case-1-book", "slotId": slot_id, "keyHash": key_hash}
        self.operation = acquire_lease(self.case, previous, version, datetime.now(timezone.utc), "book")
        return {"case": copy.deepcopy(self.case), "operation": copy.deepcopy(self.operation)}

    def commit_booking(self, lease, appointment):
        check_lease(self.case, self.operation, lease["operation"], datetime.now(timezone.utc))
        self.case.update(status="BOOKED", appointment=appointment, bookingKeyHash=lease["operation"]["keyHash"], recoveryPhase=None)
        self.case["currentVersion"] += 1
        self.operation["leaseToken"] = None
        return copy.deepcopy(self.case)

    def fail_booking(self, lease):
        self.case.update(status="ERROR", recoveryPhase="book", pendingSlotId=lease["operation"]["slotId"])
        self.case["currentVersion"] += 1
        self.operation["leaseToken"] = None
        return copy.deepcopy(self.case)

    def close_case(self, case_id):
        if self.case["status"] not in {"BOOKED", "CLOSED"}: raise CaseConflict
        self.case["status"] = "CLOSED"
        return copy.deepcopy(self.case)


class BookingGateway:
    def __init__(self, slot, drop=False): self.slot = slot; self.drop = drop; self.operations = []
    async def exchange(self, request):
        self.operations.append(request.operation_id)
        if self.drop:
            self.drop = False
            raise TimeoutError("Lost booking response")
        return ExchangeResponse(display_text="Simulated booking confirmed", next_stage="booked", reference="DEMO-1",
                                context_id="context-1", appointment={
                                    "slotId": self.slot["id"], "start": self.slot["start"], "end": self.slot["end"],
                                    "timezone": "Asia/Kolkata", "bookingReference": "BOOK-DEMO-1", "simulated": True})


@pytest.mark.asyncio
async def test_dismissal_creates_no_booking_and_stale_slot_conflicts():
    store = BookingStore()
    gateway = BookingGateway(store.slot)
    service = CaseService(None, store, gateway=gateway)
    assert len(service.slots("case-1")) == 1
    assert store.case["status"] == "AWAITING_APPOINTMENT" and gateway.operations == []
    with pytest.raises(CaseConflict):
        await service.book("case-1", "expired-slot", "fictional-booking-key")


@pytest.mark.asyncio
async def test_lost_booking_replays_same_operation_and_appointment():
    store = BookingStore()
    gateway = BookingGateway(store.slot, drop=True)
    service = CaseService(None, store, gateway=gateway)
    failed = await service.book("case-1", "slot-1", "fictional-booking-key")
    assert failed["status"] == "ERROR" and failed["recoveryPhase"] == "book"
    booked = await service.book("case-1", "slot-1", "fictional-booking-key")
    replay = await service.book("case-1", "slot-1", "fictional-booking-key")
    assert replay["appointment"] == booked["appointment"]
    assert gateway.operations == ["case-1-book", "case-1-book"]
    with pytest.raises(CaseConflict):
        await service.book("case-1", "different-slot", "different-booking-key")


@pytest.mark.asyncio
async def test_booking_can_recover_after_browser_loses_request_key():
    store = BookingStore()
    gateway = BookingGateway(store.slot, drop=True)
    await CaseService(None, store, gateway=gateway).book("case-1", "slot-1", "fictional-original-key")
    recovered = await CaseService(None, store, gateway=gateway).book("case-1", "slot-1", "fictional-refreshed-key")
    assert recovered["status"] == "BOOKED"
    assert gateway.operations == ["case-1-book", "case-1-book"]


def test_closure_requires_booked_case_and_true_confirmation():
    store = BookingStore()
    service = CaseService(None, store)
    store.case["status"] = "PROCESSING"
    with pytest.raises(CaseConflict): service.confirm_resolution("case-1", True)
    store.case["status"] = "BOOKED"
    with pytest.raises(CaseConflict): service.confirm_resolution("case-1", False)
    assert service.confirm_resolution("case-1", True)["status"] == "CLOSED"
