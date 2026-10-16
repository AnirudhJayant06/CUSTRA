"""Authenticated complaint records and validation."""

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.api.auth import ApiError
from app.services.auth import require_session
from app.services.cases import CaseValidationError, IdempotencyConflict
from app.services.leases import CaseConflict


router = APIRouter(prefix="/api/complaints", dependencies=[Depends(require_session)])


@router.post("")
def create_complaint(payload: dict, request: Request,
                           idempotency_key: str | None = Header(default=None)):
    try:
        return request.app.state.cases.create(payload, idempotency_key or "")
    except CaseValidationError as exc:
        raise ApiError(422, "invalid_input", str(exc), field_errors=exc.field_errors) from exc
    except IdempotencyConflict as exc:
        raise ApiError(409, "idempotency_conflict", "This request key was used with different details") from exc


@router.get("")
def list_complaints(request: Request, productId: str | None = None):
    return request.app.state.cases.list(productId)


@router.get("/{case_id}")
def get_complaint(case_id: str, request: Request):
    try:
        return request.app.state.cases.get(case_id)
    except LookupError as exc:
        raise ApiError(404, "not_found", "Complaint not found") from exc


class AdvanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expectedVersion: int = Field(ge=0)


@router.post("/{case_id}/advance")
async def advance(case_id: str, payload: AdvanceInput, request: Request):
    if not request.app.state.settings.agent_enabled:
        raise ApiError(503, "agent_disabled", "Agent processing is disabled", False)
    try:
        return await request.app.state.cases.advance(case_id, payload.expectedVersion)
    except CaseConflict as exc:
        raise ApiError(409, "case_conflict", str(exc), True) from exc
    except LookupError as exc:
        raise ApiError(404, "not_found", "Complaint not found") from exc


@router.get("/{case_id}/events")
def events(case_id: str, request: Request, after: int = 0):
    if after < 0:
        raise ApiError(422, "invalid_input", "Event cursor must be nonnegative")
    try:
        request.app.state.cases.get(case_id)
    except LookupError as exc:
        raise ApiError(404, "not_found", "Complaint not found") from exc
    return request.app.state.cases.store.events(case_id, after)


class BookingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slotId: str = Field(min_length=1, max_length=100)


class ResolutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: StrictBool


@router.get("/{case_id}/slots")
def slots(case_id: str, request: Request):
    try:
        return request.app.state.cases.slots(case_id)
    except CaseConflict as exc:
        raise ApiError(409, "case_conflict", str(exc)) from exc
    except LookupError as exc:
        raise ApiError(404, "not_found", "Complaint not found") from exc


@router.post("/{case_id}/appointment")
async def book(case_id: str, payload: BookingInput, request: Request,
               idempotency_key: str | None = Header(default=None)):
    try:
        return await request.app.state.cases.book(case_id, payload.slotId, idempotency_key or "")
    except CaseConflict as exc:
        raise ApiError(409, "case_conflict", str(exc), True) from exc
    except LookupError as exc:
        raise ApiError(404, "not_found", "Complaint not found") from exc


@router.post("/{case_id}/confirm-resolution")
def confirm_resolution(case_id: str, payload: ResolutionInput, request: Request):
    try:
        return request.app.state.cases.confirm_resolution(case_id, payload.confirmed)
    except CaseConflict as exc:
        raise ApiError(409, "case_conflict", str(exc)) from exc
    except LookupError as exc:
        raise ApiError(404, "not_found", "Complaint not found") from exc
