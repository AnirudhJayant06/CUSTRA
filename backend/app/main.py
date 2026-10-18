"""Custra API assembly and shared security boundaries."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import GoogleAuthError

from app.api.auth import ApiError, router as auth_router
from app.api.account import router as account_router
from app.api.products import router as products_router
from app.api.documents import router as documents_router
from app.api.complaints import router as complaints_router
from app.config import Settings
from app.services.repository import FirestoreCaseStore, FirestoreDocumentStore, FirestoreSessionStore, FirestoreVaultStore, SessionStore
from app.services.vault import VaultService
from app.services.files import CloudBucket, FileService
from app.services.cases import CaseService
from app.agents.consumer import ConsumerAgent
from app.services.upload_limit import UploadLimitMiddleware


def create_app(settings: Settings | None = None, session_store: SessionStore | None = None,
               vault_store=None, file_store=None, file_bucket=None, case_store=None, knowledge_records=None, knowledge_model=None) -> FastAPI:
    app = FastAPI(title="Custra API")
    app.state.settings = settings or Settings.from_env()
    app.state.session_store = session_store or FirestoreSessionStore(app.state.settings.project_id)
    app.state.vault = VaultService(vault_store or FirestoreVaultStore(app.state.settings.project_id))
    app.state.files = FileService(
        file_bucket or CloudBucket(app.state.settings.project_id, app.state.settings.bucket),
        file_store or FirestoreDocumentStore(app.state.settings.project_id),
    )
    app.state.cases = CaseService(
        app.state.vault, case_store or FirestoreCaseStore(app.state.settings.project_id),
        consumer=ConsumerAgent(app.state.settings.model_id, app.state.settings.project_id, app.state.settings.model_location),
        a2a_url=app.state.settings.a2a_url,
        agent_enabled=app.state.settings.agent_enabled,
        a2a_iam_auth=app.state.settings.a2a_iam_auth,
    )

    app.state.cases.files = app.state.files
    app.state.knowledge = None
    if app.state.settings.natural_conversation and (app.state.settings.project_id or knowledge_model):
        from app.agents.knowledge import KnowledgeModel
        from app.services.knowledge import KnowledgeService
        from app.services.records import FirestoreRecords
        from app.services.conversation import ConversationService
        model = knowledge_model or KnowledgeModel(app.state.settings.model_id, app.state.settings.project_id,
            app.state.settings.model_location, app.state.settings.embedding_model, app.state.settings.embedding_location)
        app.state.knowledge = KnowledgeService(knowledge_records or FirestoreRecords(app.state.settings.project_id),
            model, app.state.files, app.state.vault)
        app.state.cases.conversation = ConversationService(app.state.cases.store, app.state.knowledge,
                                                         model, app.state.cases._exchange)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") != app.state.settings.app_origin.rstrip("/"):
                response = JSONResponse(status_code=403, content={
                    "code": "origin_not_allowed", "message": "Request origin is not allowed", "retryable": False,
                })
            elif request.headers.get("sec-fetch-site") == "cross-site":
                response = JSONResponse(status_code=403, content={
                    "code": "origin_not_allowed", "message": "Request origin is not allowed", "retryable": False,
                })
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    @app.exception_handler(ApiError)
    async def api_error(_request: Request, exc: ApiError):
        content = {
            "code": exc.code, "message": exc.message, "retryable": exc.retryable,
        }
        if exc.field_errors:
            content["field_errors"] = exc.field_errors
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        fields = {str(error["loc"][-1]): error["msg"] for error in exc.errors()}
        return JSONResponse(status_code=422, content={
            "code": "invalid_input", "message": "Check the highlighted fields",
            "retryable": False, "field_errors": fields,
        })

    @app.exception_handler(GoogleAPICallError)
    @app.exception_handler(GoogleAuthError)
    async def cloud_error(_request: Request, _exc: Exception):
        return JSONResponse(status_code=503, content={
            "code": "service_unavailable",
            "message": "A required service is unavailable. Try again shortly.",
            "retryable": True,
        }, headers={"Cache-Control": "private, no-store"})

    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "service": "Custra Backend"}

    app.include_router(auth_router)
    app.include_router(account_router)
    app.include_router(products_router)
    app.include_router(documents_router)
    app.include_router(complaints_router)
    app.add_middleware(UploadLimitMiddleware)
    return app


app = create_app()
