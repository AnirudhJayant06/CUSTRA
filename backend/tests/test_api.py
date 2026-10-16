"""Public health and private session boundary checks for the current API."""

import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://api.test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "Custra Backend"}


@pytest.mark.asyncio
async def test_session_requires_login():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://api.test") as client:
        response = await client.get("/api/auth/session")
    assert response.status_code == 401
    assert response.json() == {
        "code": "unauthorized", "message": "Sign in to continue", "retryable": False,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize('method,path', [
    ('GET', '/api/profile'), ('PATCH', '/api/profile'),
    ('GET', '/api/addresses'), ('POST', '/api/addresses'),
    ('GET', '/api/products'), ('POST', '/api/products'),
    ('GET', '/api/catalog'), ('GET', '/api/service-centers'),
    ('GET', '/api/documents/fictional/content'),
    ('POST', '/api/products/fictional/documents'),
    ('GET', '/api/complaints'), ('POST', '/api/complaints'),
    ('GET', '/api/complaints/fictional'), ('GET', '/api/complaints/fictional/events'),
    ('POST', '/api/complaints/fictional/advance'), ('GET', '/api/complaints/fictional/slots'),
    ('POST', '/api/complaints/fictional/appointment'),
    ('POST', '/api/complaints/fictional/confirm-resolution'),
    ('POST', '/api/complaints/fictional/documents'),
])
async def test_data_and_agent_routes_reject_direct_unauthenticated_calls(method, path):
    # No credentials or backing services are configured: authentication must
    # reject the request before any store, upload or model access.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://api.test') as client:
        response = await client.request(method, path)
    assert response.status_code == 401
    assert response.json()['code'] == 'unauthorized'
    assert response.headers['cache-control'] == 'private, no-store'
