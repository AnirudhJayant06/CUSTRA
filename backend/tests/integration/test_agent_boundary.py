"""Real SDK A2A transport checks; the Gemini check is opt-in and cloud-dependent."""

import asyncio
import importlib.util
import sys
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.models.exchange import ExchangeRequest, ExchangeResponse
from app.services.a2a_gateway import A2AGateway


def business_app():
    path = Path(__file__).resolve().parents[3] / "manufacturer-agent/app/main.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("business_app", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    class ReplayStore:
        def __init__(self): self.operations = {}; self.states = {}
        def transact(self, operation_id, digest, case_id, generate):
            if operation_id in self.operations:
                old_digest, result = self.operations[operation_id]
                if old_digest != digest: raise ValueError("Changed payload")
                return result
            result, state = generate(self.states.get(case_id, {}))
            self.states[case_id] = state
            self.operations[operation_id] = (digest, result)
            return result

    return module.create_app("http://business.test", store=ReplayStore())


@pytest.mark.asyncio
async def test_real_a2a_start_and_answer():
    transport = httpx.ASGITransport(app=business_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://business.test") as client:
        gateway = A2AGateway("http://business.test", client)
        start = await gateway.exchange(ExchangeRequest(
            schema_version=1, case_id="case-fictional-1", operation_id="op-start",
            scenario_id="basic", action="start", stage="new", data={},
        ))
        assert start.question_code == "product"
        assert start.requested_fields == ["product.brand", "product.model"]
        assert start.context_id and start.message_id

        answer = await gateway.exchange(ExchangeRequest(
            schema_version=1, case_id="case-fictional-1", operation_id="op-answer",
            scenario_id="basic", action="answer", stage=start.next_stage,
            data={"product.brand": "Acme", "product.model": "Example 1"},
            context_id=start.context_id,
        ))
        assert answer.question_code == "issue"
        assert answer.context_id == start.context_id
        assert answer.message_id != start.message_id


@pytest.mark.asyncio
async def test_real_a2a_rejects_malformed_reply():
    transport = httpx.ASGITransport(app=business_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://business.test") as client:
        gateway = A2AGateway("http://business.test", client)
        with pytest.raises(ValueError):
            await gateway.exchange(ExchangeRequest(
                schema_version=1, case_id="case-fictional-2", operation_id="bad",
                scenario_id="basic", action="answer", stage="product",
                data={"product.brand": "Acme"},
            ))


def test_exchange_response_rejects_unexpected_or_missing_data():
    with pytest.raises(ValidationError):
        ExchangeResponse.model_validate({"display_text": "", "next_stage": "issue", "made_up": True})


@pytest.mark.asyncio
async def test_live_vertex_consumer_answer():
    import os

    if os.getenv("CUSTRA_RUN_LIVE_MODEL") != "1":
        pytest.skip("Set CUSTRA_RUN_LIVE_MODEL=1 only after confirming local ADC and project")
    from app.agents.consumer import ConsumerAgent
    from app.models.exchange import ExchangeResponse

    agent = ConsumerAgent(model="gemini-3.5-flash-lite")
    answer = await asyncio.wait_for(agent.answer(
        ExchangeResponse(question_code="product", requested_fields=["product.brand", "product.model"],
                         display_text="Which product needs service?", next_stage="issue"),
        facts={"product": {"brand": "Acme", "model": "Example 1"}}, transcript=[],
    ), timeout=35)
    assert answer.text
    assert set(answer.field_refs) == {"product.brand", "product.model"}


@pytest.mark.asyncio
async def test_natural_a2a_attachment_is_transferred_and_receipted_without_field_hints():
    import hashlib
    import base64
    content = b'%PDF-1.7 fictional invoice'
    version = hashlib.sha256(content).hexdigest()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=business_app()), base_url='http://business.test') as client:
        gateway = A2AGateway('http://business.test', client)
        response = await gateway.exchange(ExchangeRequest(schema_version=1, case_id='natural-file', operation_id='n-start',
            scenario_id='natural', action='start', stage='new', data={'request_document': True}))
        assert response.requested_fields == []
        for i in range(5):
            response = await gateway.exchange(ExchangeRequest(schema_version=1, case_id='natural-file', operation_id=f'n-{i}',
                scenario_id='natural', action='answer', stage=response.next_stage, data={'text': 'Fictional supported answer'}, context_id=response.context_id))
        assert response.next_stage == 'receipt'
        response = await gateway.exchange(ExchangeRequest(schema_version=1, case_id='natural-file', operation_id='n-share',
            scenario_id='natural', action='answer', stage='receipt', data={'text': 'Requested invoice attached'}, context_id=response.context_id,
            attachment={'documentId': 'd1', 'version': version, 'filename': 'invoice.pdf', 'mediaType': 'application/pdf',
                        'content': base64.b64encode(content).decode('ascii')}))
        assert response.attachment_receipt == version
        assert response.next_stage == 'registered'


@pytest.mark.asyncio
async def test_live_knowledge_resolves_purchase_paraphrases_without_runtime_field_hints():
    """Separate evaluator; actual understanding requires this paid opt-in test."""
    import os
    if os.getenv('CUSTRA_RUN_KNOWLEDGE_MODEL') != '1':
        pytest.skip('Opt in to at most eight real resolver/answer calls')
    assert os.getenv('GOOGLE_CLOUD_PROJECT') == 'custra-mvp-2026', 'Dedicated Custra project required'
    from app.agents.knowledge import KnowledgeModel
    model = KnowledgeModel(os.getenv('CUSTRA_MODEL_ID', 'gemini-3.5-flash-lite'), 'custra-mvp-2026')
    questions = ['What date did you purchase this appliance?', 'When was this product bought?',
                 'Could you provide its purchase date?', 'And when did you buy it?']
    for index, question in enumerate(questions):
        resolution = await model.resolve(question, {'product': {'model': 'WM-100'},
            'history': [{'role': 'business', 'displayText': 'What model is the appliance?'},
                        {'role': 'consumer', 'displayText': 'WM-100'}]})
        # Expected values belong to the evaluator, never the resolver input.
        assert resolution.requested_facts == ['product.purchaseDate']
        date = ['2025-01-12', '2025-04-03', '2026-02-15', '2026-06-09'][index]
        answer = await model.compose(resolution.standalone_question, [
            {'id': 'purchase', 'field': 'product.purchaseDate', 'value': date, 'text': date},
            {'id': 'serial', 'field': 'product.serialNumber', 'value': 'SN-999', 'text': 'SN-999'}])
        assert answer.values.get('product.purchaseDate') == date
        assert date in answer.text and not answer.missing
