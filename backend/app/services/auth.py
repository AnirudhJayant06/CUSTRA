"""Password verification and opaque, expiring demo sessions."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Request

from app.services.repository import SessionStore


SESSION_SECONDS = 8 * 60 * 60
PBKDF2_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or not 100_000 <= int(iterations) <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class DemoSession:
    token_hash: str
    expires_at: datetime


def create_session(store: SessionStore) -> tuple[str, DemoSession]:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(seconds=SESSION_SECONDS)
    digest = token_digest(token)
    store.create(digest, expires)
    return token, DemoSession(digest, expires)


def require_session(request: Request) -> DemoSession:
    from app.api.auth import ApiError

    token = request.cookies.get("__session")
    if not token:
        raise ApiError(401, "unauthorized", "Sign in to continue")
    digest = token_digest(token)
    record = request.app.state.session_store.get(digest)
    expires = record.get("expires_at") if record else None
    if not record or record.get("revoked") or not isinstance(expires, datetime):
        raise ApiError(401, "unauthorized", "Sign in to continue")
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        raise ApiError(401, "unauthorized", "Sign in to continue")
    return DemoSession(digest, expires)
