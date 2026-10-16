import pytest

from app.agents.consumer import validate_answer
from app.models.exchange import ExchangeResponse


QUESTION = ExchangeResponse(
    question_code="product", requested_fields=["product.brand", "product.model"],
    display_text="Which product needs service?", next_stage="product",
)
FACTS = {"product": {"brand": "Acme", "model": "Example 1"}}


def test_answer_accepts_supplied_field_references():
    result = validate_answer(
        {"text": "Brand: Acme; Model: Example 1", "field_refs": ["product.brand", "product.model"]},
        QUESTION, FACTS,
    )
    assert result.field_refs == QUESTION.requested_fields


@pytest.mark.parametrize("reply", [
    {"text": "An Acme device", "field_refs": ["product.brand", "profile.phone"]},
    {"text": "An Acme device", "field_refs": ["product.brand", "product.model", "product.serial"]},
    {"text": "An Acme device", "field_refs": ["product.brand"]},
])
def test_answer_rejects_unsupported_or_missing_references(reply):
    with pytest.raises(ValueError):
        validate_answer(reply, QUESTION, FACTS)


def test_answer_rejects_invented_content_even_with_valid_refs():
    with pytest.raises(ValueError):
        validate_answer({"text": "Brand: Acme; Model: Example 1. Lifetime warranty included.",
                         "field_refs": QUESTION.requested_fields}, QUESTION, FACTS)


def test_business_slots_require_dates_timezone_and_simulation_marker():
    with pytest.raises(ValueError):
        ExchangeResponse(display_text="Registered", next_stage="registered", reference="DEMO-1",
                         slots=[{"id": "made-up", "start": "tomorrow"}])


@pytest.mark.asyncio
async def test_consumer_uses_explicit_vertex_project_with_one_request(monkeypatch):
    """Exercise the real ADK/GenAI path without contacting Google or loading ADC."""
    import json
    import httpx
    import google.genai
    from google.auth.credentials import AnonymousCredentials
    from app.agents.consumer import ConsumerAgent

    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"candidates": [{"content": {
            "role": "model", "parts": [{"text": json.dumps({
                "text": "Brand: Acme; Model: Example 1",
                "field_refs": ["product.brand", "product.model"],
            })}]}, "finishReason": "STOP"}]})

    real_client = google.genai.Client
    def offline_client(**kwargs):
        credentials = AnonymousCredentials()
        credentials.token = "fictional-offline-token"
        kwargs["credentials"] = credentials
        kwargs["http_options"].async_client_args = {"transport": httpx.MockTransport(respond)}
        return real_client(**kwargs)

    monkeypatch.setattr(google.genai, "Client", offline_client)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "wrong-default-project")
    result = await ConsumerAgent("gemini-3.5-flash-lite", "fictional-explicit-project").answer(QUESTION, FACTS, [])
    assert result.text == "Brand: Acme; Model: Example 1"
    assert len(requests) == 1
    assert requests[0].url.host == "aiplatform.googleapis.com"
    assert "/projects/fictional-explicit-project/locations/global/" in requests[0].url.path
