"""Authenticated backend proxy for private demo documents."""

import asyncio
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.api.auth import ApiError
from app.services.auth import require_session


router = APIRouter(prefix="/api", dependencies=[Depends(require_session)])


@router.get("/products/{product_id}/documents")
def list_product_documents(product_id: str, request: Request):
    try:
        request.app.state.vault.get_product(product_id)
    except LookupError as exc:
        raise ApiError(404, "not_found", "Product not found") from exc
    return request.app.state.files.list_for_parent("product", product_id)


@router.post("/products/{product_id}/documents")
def upload_product_document(product_id: str, request: Request, file: UploadFile = File(...)):
    try:
        request.app.state.vault.get_product(product_id)
    except LookupError as exc:
        raise ApiError(404, "not_found", "Product not found") from exc
    try:
        return request.app.state.files.upload("product", product_id, file.filename or "",
                                               file.file, file.content_type or "")
    except ValueError as exc:
        raise ApiError(422, "invalid_file", str(exc)) from exc
    except OSError as exc:
        raise ApiError(503, "upload_failed", "Document upload failed; try again", True) from exc


@router.get("/documents/{document_id}/content")
async def download_document(document_id: str, request: Request):
    try:
        record, stream = await asyncio.to_thread(request.app.state.files.open, document_id)
    except LookupError as exc:
        raise ApiError(404, "not_found", "Document not found") from exc

    async def chunks():
        with stream:
            while chunk := await asyncio.to_thread(stream.read, 64 * 1024):
                yield chunk

    disposition = "attachment" if record["mediaType"] == "application/pdf" else "inline"
    safe_name = quote(record["originalName"], safe="")
    return StreamingResponse(chunks(), media_type=record["mediaType"], headers={
        "Content-Disposition": f"{disposition}; filename*=UTF-8''{safe_name}",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    })


@router.get("/complaints/{case_id}/documents")
def list_case_documents(case_id: str, request: Request):
    try:
        request.app.state.cases.get(case_id)
    except LookupError as exc:
        raise ApiError(404, "not_found", "Complaint not found") from exc
    return request.app.state.files.list_for_parent("case", case_id)


@router.post("/complaints/{case_id}/documents")
def upload_case_document(case_id: str, request: Request, file: UploadFile = File(...)):
    try:
        case = request.app.state.cases.get(case_id)
    except LookupError as exc:
        raise ApiError(404, "not_found", "Complaint not found") from exc
    if case['status'] == 'CLOSED':
        raise ApiError(409, 'case_closed', 'This chat is closed. Start a new complaint to add documents.')
    try:
        return request.app.state.files.upload("case", case_id, file.filename or "", file.file, file.content_type or '')
    except ValueError as exc:
        raise ApiError(422, "invalid_file", str(exc)) from exc
    except OSError as exc:
        raise ApiError(503, "upload_failed", "Document upload failed; try again", True) from exc
