import httpx
import pytest
from google.protobuf.json_format import MessageToDict
from a2a.types import AgentCard, AgentInterface, AgentCapabilities

from app.models.exchange import ExchangeRequest
from app.services.a2a_gateway import A2AGateway


@pytest.mark.asyncio
async def test_agent_card_cannot_redirect_gateway_to_another_host():
    calls = []
    card = AgentCard(name="Fictional business", version="1", description="Demo",
                     capabilities=AgentCapabilities(), default_input_modes=["application/json"],
                     default_output_modes=["application/json"],
                     supported_interfaces=[AgentInterface(url="https://untrusted.example/a2a", protocol_binding="JSONRPC", protocol_version="1.0")])
    async def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json=MessageToDict(card))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = A2AGateway("http://business.test", client)
        with pytest.raises(ValueError):
            await gateway.exchange(ExchangeRequest(schema_version=1, case_id="fictional", operation_id="fictional-op",
                                                    scenario_id="basic", action="start", stage="new", data={}))
    assert calls == ["http://business.test/.well-known/agent-card.json"]


@pytest.mark.asyncio
async def test_cloud_run_identity_auth_covers_card_and_exchange(monkeypatch):
    from app.services.a2a_gateway import CloudRunAuth
    from google.oauth2 import id_token

    audiences = []
    def fetch(_request, audience):
        audiences.append(audience)
        return "fictional-identity-token"
    monkeypatch.setattr(id_token, "fetch_id_token", fetch)
    paths = []
    async def handler(request):
        assert request.headers["authorization"] == "Bearer fictional-identity-token"
        paths.append(request.url.path)
        return httpx.Response(200, json={})
    async with httpx.AsyncClient(auth=CloudRunAuth("https://business.example"), transport=httpx.MockTransport(handler)) as client:
        await client.get("https://business.example/.well-known/agent-card.json")
        await client.post("https://business.example/a2a", json={})
    assert paths == ["/.well-known/agent-card.json", "/a2a"]
    assert audiences == ["https://business.example", "https://business.example"]
