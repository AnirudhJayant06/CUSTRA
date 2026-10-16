"""Private A2A simulator application; Cloud Run IAM will gate access."""

import os
from fastapi import FastAPI

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentInterface, AgentSkill

from executor import BusinessExecutor
from store import FirestoreReplayStore


def create_app(base_url: str, store=None) -> FastAPI:
    card = AgentCard(
        name="Custra demo business simulator", description="Scripted fictional complaint flow",
        version="0.1.0", capabilities=AgentCapabilities(streaming=False),
        supported_interfaces=[AgentInterface(url=base_url + "/a2a", protocol_binding="JSONRPC", protocol_version="1.0")],
        default_input_modes=["application/json"], default_output_modes=["application/json"],
        skills=[AgentSkill(id="demo-complaint", name="Demo complaint", description="Fictional service questions", tags=["demo"])],
    )
    handler = DefaultRequestHandler(BusinessExecutor(store or FirestoreReplayStore(os.getenv("GOOGLE_CLOUD_PROJECT", ""))), InMemoryTaskStore(), card)
    app = FastAPI()
    add_a2a_routes_to_fastapi(
        app, agent_card_routes=create_agent_card_routes(card),
        jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url="/a2a"),
    )
    return app


app = create_app(os.getenv("CUSTRA_PUBLIC_URL", "http://127.0.0.1:8080"))
