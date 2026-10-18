"""Offline model/storage doubles; these do not evaluate language understanding."""
import copy
import threading
from app.models.knowledge import Resolution, GroundedAnswer

class Records:
    def __init__(self): self.rows = {}; self.lock = threading.RLock()
    def get(self, kind, key):
        with self.lock: return copy.deepcopy(self.rows.get((kind, key)))
    def mutate(self, kind, key, fn):
        with self.lock:
            value = fn(self.get(kind, key)); self.rows[kind, key] = copy.deepcopy(value)
            return copy.deepcopy(value)
    def list(self, kind):
        return [copy.deepcopy(value) for (k, _), value in self.rows.items() if k == kind]

class FixtureModel:
    """A scripted response queue, never a production question-to-field mapper."""
    def __init__(self, request_document=False): self.resolve_calls = 0; self.request_document = request_document; self.fail_answers = 0
    async def resolve(self, question, context):
        responses = [
            ['product.brand', 'product.model'], ['issue.description'],
            ['profile.name', 'profile.phone', 'profile.email'],
            ['address.line1', 'address.city', 'address.postal_code'], ['product.purchaseDate']]
        if self.request_document and self.resolve_calls >= 5:
            return Resolution(standalone_question=question, requires_document=True, document_type='invoice')
        fields = responses[min(self.resolve_calls, len(responses)-1)]
        self.resolve_calls += 1
        return Resolution(standalone_question=question, requested_facts=fields)
    async def compose(self, question, evidence):
        if self.fail_answers:
            self.fail_answers -= 1
            raise ValueError('Injected offline answer failure')
        values = {e['field']: e['value'] for e in evidence if 'field' in e}
        return GroundedAnswer(text='; '.join(values.values()) or evidence[0]['text'],
            citations=[e['id'] for e in evidence], values=values)
    async def extract(self, data, media_type, context):
        return {'document_type': 'invoice', 'description': 'Fictional product invoice', 'product_match': True,
            'facts': [{'field': 'product.purchaseDate', 'value': '2026-02-12', 'quote': 'Purchased 2026-02-12', 'page': 1}],
            'passages': [{'text': 'Purchased 2026-02-12. Invoice INV-123. Fiction Branch.', 'page': 1}]}
    async def embed(self, texts, query=False): return [[1., 0., 0.] for _ in texts]
