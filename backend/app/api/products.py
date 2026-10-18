"""Authenticated manual Vault product and demo fixture routes."""

from fastapi import APIRouter, Depends, Request

from app.api.auth import ApiError
from app.models.product import ProductInput
from app.services.auth import require_session
from app.services.leases import CaseConflict


router = APIRouter(prefix="/api", dependencies=[Depends(require_session)])


@router.get("/catalog")
def catalog(request: Request):
    return request.app.state.vault.catalog()


@router.get("/service-centers")
def service_centers(request: Request):
    return request.app.state.vault.service_centers()


@router.get("/products")
def list_products(request: Request):
    return request.app.state.vault.list_products()


@router.post("/products")
def create_product(payload: ProductInput, request: Request):
    try:
        return request.app.state.vault.create_product(payload.model_dump(mode="json"))
    except ValueError as exc:
        raise ApiError(422, "invalid_input", str(exc)) from exc


@router.get("/products/{product_id}")
def get_product(product_id: str, request: Request):
    try:
        return request.app.state.vault.get_product(product_id)
    except LookupError as exc:
        raise ApiError(404, "not_found", "Product not found") from exc


@router.patch("/products/{product_id}")
def update_product(product_id: str, changes: dict, request: Request):
    try:
        saved = request.app.state.vault.update_product(product_id, changes)
        if request.app.state.knowledge:
            request.app.state.knowledge.sync_product_fields(saved, set(changes))
        return saved
    except LookupError as exc:
        raise ApiError(404, "not_found", "Product not found") from exc
    except ValueError as exc:
        raise ApiError(422, "invalid_input", str(exc)) from exc


@router.delete('/products/{product_id}')
def delete_product(product_id: str, request: Request):
    try:
        return request.app.state.cases.store.delete_product(product_id)
    except LookupError as exc:
        raise ApiError(404, 'not_found', 'Product not found') from exc
    except CaseConflict as exc:
        raise ApiError(409, 'case_conflict', str(exc), True) from exc
