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
    except CaseConflict as exc:
        raise ApiError(409, 'case_conflict', str(exc), True) from exc


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


class CustomerInput(AdvanceInput):
    text: str = Field(default='', max_length=2000)
    values: dict[str, str] = Field(default_factory=dict, max_length=8)
    documentId: str | None = Field(default=None, max_length=128)


class ShareInput(AdvanceInput):
    documentId: str = Field(min_length=1, max_length=128)
    documentVersion: str = Field(min_length=64, max_length=64)


def conversation(request):
    service = request.app.state.cases.conversation
    if not service:
        raise ApiError(409, 'conversation_unavailable', 'This conversation does not support this action')
    if not request.app.state.settings.agent_enabled:
        raise ApiError(503, 'agent_disabled', 'Agent processing is disabled')
    return service


@router.post('/{case_id}/input')
async def customer_input(case_id: str, payload: CustomerInput, request: Request):
    try:
        return await conversation(request).submit_input(case_id, payload.expectedVersion,
            payload.text, payload.values, payload.documentId)
    except CaseConflict as exc:
        raise ApiError(409, 'case_conflict', str(exc)) from exc
    except (ValueError, LookupError) as exc:
        raise ApiError(422, 'invalid_input', str(exc)) from exc


@router.post('/{case_id}/continue')
def continue_without_detail(case_id: str, payload: AdvanceInput, request: Request):
    try:
        return conversation(request).continue_without_detail(case_id, payload.expectedVersion)
    except CaseConflict as exc:
        raise ApiError(409, 'case_conflict', str(exc)) from exc


@router.post('/{case_id}/share')
def share(case_id: str, payload: ShareInput, request: Request):
    try:
        return conversation(request).share(case_id, payload.expectedVersion, payload.documentId, payload.documentVersion)
    except CaseConflict as exc:
        raise ApiError(409, 'case_conflict', str(exc)) from exc
    except (ValueError, LookupError) as exc:
        raise ApiError(422, 'invalid_document', str(exc)) from exc
