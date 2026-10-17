"""Authenticated shared profile and address routes."""

from fastapi import APIRouter, Depends, Request

from app.api.auth import ApiError
from app.models.account import AddressInput, ProfileInput
from app.services.auth import require_session


router = APIRouter(prefix="/api", dependencies=[Depends(require_session)])


@router.get("/profile")
def get_profile(request: Request):
    return request.app.state.vault.get_profile()


@router.patch("/profile")
def save_profile(payload: ProfileInput, request: Request):
    return request.app.state.vault.save_profile(payload.model_dump())


@router.get("/addresses")
def list_addresses(request: Request):
    return request.app.state.vault.list_addresses()


@router.post("/addresses")
def create_address(payload: AddressInput, request: Request):
    return request.app.state.vault.create_address(payload.model_dump())


@router.patch("/addresses/{address_id}")
def update_address(address_id: str, changes: dict, request: Request):
    try:
        return request.app.state.vault.update_address(address_id, changes)
    except LookupError as exc:
        raise ApiError(404, "not_found", "Address not found") from exc
    except ValueError as exc:
        raise ApiError(422, "invalid_input", str(exc)) from exc


@router.put('/profile/default-address/{address_id}')
def set_default_address(address_id: str, request: Request):
    try:
        return request.app.state.vault.set_default_address(address_id)
    except LookupError as exc:
        raise ApiError(404, 'not_found', 'Address not found') from exc


@router.get('/availability')
def availability():
    from app.services.demo_schedule import demo_schedule
    return {'slots': demo_schedule(), 'simulated': True, 'timezone': 'Asia/Kolkata'}
