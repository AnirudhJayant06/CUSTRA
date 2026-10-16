"""Demo sign-in, session check and revocation."""

import hmac

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.services.auth import SESSION_SECONDS, create_session, require_session, verify_password


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, retryable: bool = False,
                 field_errors: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.field_errors = field_errors


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


router = APIRouter(prefix="/api/auth")


@router.post("/login")
def login(body: Credentials, request: Request):
    settings = request.app.state.settings
    if not settings.demo_username or not settings.password_hash:
        raise ApiError(503, "login_unconfigured", "Demo login is not configured", True)
    username_ok = hmac.compare_digest(body.username.encode(), settings.demo_username.encode())
    password_ok = verify_password(body.password, settings.password_hash)
    if not username_ok or not password_ok:
        raise ApiError(401, "invalid_credentials", "Invalid credentials")
    token, _ = create_session(request.app.state.session_store)
    from fastapi.responses import JSONResponse

    response = JSONResponse({"authenticated": True})
    response.set_cookie("__session", token, max_age=SESSION_SECONDS, httponly=True,
                        secure=settings.secure_cookies, samesite="lax", path="/")
    return response


@router.get("/session")
def session_check(session=Depends(require_session)):
    return {"authenticated": True, "sharedDemo": True}


@router.post("/logout")
def logout(request: Request, session=Depends(require_session)):
    request.app.state.session_store.revoke(session.token_hash)
    from fastapi.responses import JSONResponse

    response = JSONResponse({"authenticated": False})
    response.delete_cookie("__session", path="/")
    return response
