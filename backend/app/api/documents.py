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
    documents = request.app.state.files.list_for_parent("product", product_id)
    if request.app.state.knowledge:
        processed = {d['id']: d for d in request.app.state.knowledge.documents(product_id)}
        documents = [{**doc, **processed.pop(doc['id'], {})} for doc in documents]
        documents.extend(processed.values())
    return documents


@router.post("/products/{product_id}/documents")
async def upload_product_document(product_id: str, request: Request, file: UploadFile = File(...)):
    try:
        request.app.state.vault.get_product(product_id)
    except LookupError as exc:
        raise ApiError(404, "not_found", "Product not found") from exc
    try:
        saved = await asyncio.to_thread(request.app.state.files.upload, "product", product_id, file.filename or "",
                                               file.file, file.content_type or "")
        if request.app.state.knowledge and request.app.state.settings.agent_enabled:
            processed = await request.app.state.knowledge.ingest(product_id, saved['id'])
            saved.update(processed)
        return saved
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


@router.post('/complaints/{case_id}/documents/{document_id}/save-to-product')
async def save_to_product(case_id: str, document_id: str, request: Request):
    if not request.app.state.knowledge or not request.app.state.settings.agent_enabled:
        raise ApiError(409, 'processing_unavailable', 'Document processing is unavailable')
    try:
        case = request.app.state.cases.get(case_id)
        if case['status'] == 'CLOSED':
            raise ApiError(409, 'case_closed', 'This chat is closed')
        return await request.app.state.knowledge.promote(case, document_id)
    except LookupError as exc:
        raise ApiError(404, 'not_found', 'Complaint or document not found') from exc
    except ValueError as exc:
        raise ApiError(422, 'invalid_document', str(exc)) from exc


@router.get('/products/{product_id}/knowledge')
def product_knowledge(product_id: str, request: Request):
    if not request.app.state.knowledge:
        raise ApiError(409, 'processing_unavailable', 'Product knowledge is unavailable')
    try:
        return request.app.state.knowledge.get(product_id)
    except LookupError as exc:
        raise ApiError(404, 'not_found', 'Product not found') from exc


@router.get('/documents/{document_id}/version')
def document_version(document_id: str, request: Request):
    import hashlib
    try:
        metadata, stream = request.app.state.files.open(document_id)
        with stream:
            content = stream.read(5_000_001)
        if len(content) > 5_000_000:
            raise ApiError(422, 'invalid_document', 'Document exceeds the sharing limit')
        return {'version': hashlib.sha256(content).hexdigest(), 'filename': metadata['originalName']}
    except LookupError as exc:
        raise ApiError(404, 'not_found', 'Document not found') from exc
