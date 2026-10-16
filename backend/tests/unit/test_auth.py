from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.config import Settings
from app.main import create_app
from app.services.auth import hash_password


class FakeSessions:
    def __init__(self):
        self.rows = {}

    def create(self, token_hash, expires_at):
        self.rows[token_hash] = {"expires_at": expires_at, "revoked": False}

    def get(self, token_hash):
        return self.rows.get(token_hash)

    def revoke(self, token_hash):
        if token_hash in self.rows:
            self.rows[token_hash]["revoked"] = True


def configured_client(secure=False):
    store = FakeSessions()
    settings = Settings(
        project_id="custra-mvp-2026", model_id="gemini-3.5-flash-lite",
        bucket="fictional-bucket", a2a_url="http://business.test",
        demo_username="fictional-reviewer", password_hash=hash_password("fictional-passphrase"),
        app_origin="https://example.test", secure_cookies=secure,
    )
    app = create_app(settings=settings, session_store=store)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://api.test"), store


def test_server_configuration_defaults_to_secure_cookie(monkeypatch):
    monkeypatch.delenv("CUSTRA_SECURE_COOKIES", raising=False)
    assert Settings.from_env().secure_cookies is True


@pytest.mark.asyncio
async def test_login_sets_session():
    client, store = configured_client(secure=True)
    assert (await client.get("/api/auth/session")).status_code == 401
    response = await client.post("/api/auth/login", json={
        "username": "fictional-reviewer", "password": "fictional-passphrase",
    }, headers={"Origin": "https://example.test"})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "__session=" in cookie and "httponly" in cookie.lower()
    assert "secure" in cookie.lower() and "max-age=28800" in cookie.lower()
    assert response.headers["cache-control"] == "private, no-store"
    assert len(store.rows) == 1
    assert "fictional-passphrase" not in str(store.rows)
    await client.aclose()


@pytest.mark.asyncio
async def test_expired_or_revoked_session_rejected():
    client, store = configured_client()
    login = await client.post("/api/auth/login", json={
        "username": "fictional-reviewer", "password": "fictional-passphrase",
    })
    assert login.status_code == 200
    token_hash = next(iter(store.rows))
    assert (await client.get("/api/auth/session")).status_code == 200
    store.rows[token_hash]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert (await client.get("/api/auth/session")).status_code == 401
    store.rows[token_hash]["expires_at"] = datetime.now(timezone.utc) + timedelta(hours=1)
    assert (await client.post("/api/auth/logout")).status_code == 200
    assert (await client.get("/api/auth/session")).status_code == 401
    await client.aclose()


@pytest.mark.asyncio
async def test_cross_origin_mutation_rejected():
    client, _ = configured_client()
    response = await client.post("/api/auth/login", json={
        "username": "fictional-reviewer", "password": "fictional-passphrase",
    }, headers={"Origin": "https://attacker.test"})
    assert response.status_code == 403
    assert response.json()["code"] == "origin_not_allowed"
    assert "set-cookie" not in response.headers
    await client.aclose()


@pytest.mark.asyncio
async def test_bad_login_is_private_json_error():
    client, _ = configured_client()
    response = await client.post("/api/auth/login", json={
        "username": "fictional-reviewer", "password": "wrong",
    })
    assert response.status_code == 401
    assert response.json() == {"code": "invalid_credentials", "message": "Invalid credentials", "retryable": False}
    assert response.headers["cache-control"] == "private, no-store"
    await client.aclose()


@pytest.mark.asyncio
async def test_unicode_username_is_rejected_without_server_error():
    client, store = configured_client()
    async with client:
        response = await client.post('/api/auth/login', json={
            'username': 'fictional-उपयोगकर्ता', 'password': 'wrong',
        })
    assert response.status_code == 401
    assert response.json()['code'] == 'invalid_credentials'
    assert not store.rows


@pytest.mark.asyncio
async def test_cloud_store_failure_returns_private_retryable_error():
    from google.api_core.exceptions import ServiceUnavailable

    class UnavailableSessions(FakeSessions):
        def get(self, token_hash):
            raise ServiceUnavailable('fictional internal infrastructure detail')

    app = create_app(session_store=UnavailableSessions())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://api.test') as client:
        client.cookies.set('__session', 'fictional-session')
        response = await client.get('/api/auth/session')
    assert response.status_code == 503
    assert response.json() == {'code': 'service_unavailable', 'message': 'A required service is unavailable. Try again shortly.', 'retryable': True}
    assert response.headers['cache-control'] == 'private, no-store'
