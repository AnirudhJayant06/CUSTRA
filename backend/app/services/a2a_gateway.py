"""Fixed-destination A2A SDK client for the demo business service."""

import asyncio
import httpx
from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.struct_pb2 import Value

from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.client.card_resolver import A2ACardResolver
from a2a.types import Message, Part, Role, SendMessageRequest
from a2a.utils.errors import A2AError

from app.models.exchange import ExchangeRequest, ExchangeResponse


class CloudRunAuth(httpx.Auth):
    def __init__(self, audience: str):
        self.audience = audience.rstrip("/")

    async def async_auth_flow(self, request):
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token

        transport = Request()
        def bounded_request(*args, **kwargs):
            kwargs.setdefault("timeout", 5)
            return transport(*args, **kwargs)
        token = await asyncio.to_thread(id_token.fetch_id_token, bounded_request, self.audience)
        request.headers["Authorization"] = f"Bearer {token}"
        yield request


class A2AGateway:
    def __init__(self, base_url: str, http_client: httpx.AsyncClient):
        self.base_url = base_url.rstrip("/")
        self.http_client = http_client

    async def exchange(self, request: ExchangeRequest) -> ExchangeResponse:
        if request.action == "answer" and not request.data:
            raise ValueError("Answer facts are required")
        factory = ClientFactory(ClientConfig(httpx_client=self.http_client, streaming=False))
        card = await A2ACardResolver(self.http_client, self.base_url).get_agent_card()
        expected_url = self.base_url + "/a2a"
        if not card.supported_interfaces or any(interface.url != expected_url for interface in card.supported_interfaces):
            raise ValueError("Business Agent Card advertised an unexpected destination")
        client = factory.create(card)
        payload = request.model_dump(exclude={"context_id", "attachment"})
        parts = []
        if request.attachment:
            import base64
            attachment = request.attachment
            payload["attachment"] = {k: v for k, v in attachment.items() if k != "content"}
            parts.append(Part(raw=base64.b64decode(attachment["content"], validate=True),
                filename=attachment["filename"], media_type=attachment["mediaType"]))
        part = Part(data=ParseDict(payload, Value()))
        message = Message(message_id=request.operation_id, role=Role.ROLE_USER, parts=[part, *parts])
        if request.context_id:
            message.context_id = request.context_id
        try:
            async for result in client.send_message(SendMessageRequest(message=message)):
                if result.HasField("message"):
                    reply = result.message
                    if not reply.parts or not reply.parts[0].HasField("data"):
                        raise ValueError("Business response lacks structured data")
                    return ExchangeResponse.model_validate({
                        **MessageToDict(reply.parts[0].data),
                        "context_id": reply.context_id,
                        "task_id": reply.task_id or None,
                        "message_id": reply.message_id,
                    })
        except A2AError as exc:
            raise ValueError("Business exchange rejected") from exc
        raise ValueError("Business service returned no completed message")
