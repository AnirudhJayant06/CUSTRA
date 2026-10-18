"""Product-local facts and source-linked vector evidence. No automatic retries."""
import asyncio
import hashlib
import math
from datetime import datetime, timezone

from app.models.knowledge import Extraction, PRODUCT_FIELDS, is_product_field


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(value):
    if not value or len(value) > 128 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in value):
        raise ValueError('Invalid record identifier')
    return value


def cosine(left, right):
    if len(left) != len(right) or not left or not all(math.isfinite(x) for x in [*left, *right]):
        raise ValueError('Incompatible evidence vectors')
    norm = math.sqrt(sum(x*x for x in left) * sum(x*x for x in right))
    return sum(x*y for x, y in zip(left, right)) / norm if norm else 0


def passage_is_certain(passage, facts, passages):
    uncertain = [f for f in facts if f.get('uncertain')]
    if any(not any(f['quote'] in p['text'] and f['page'] == p['page'] for p in passages) for f in uncertain):
        return False
    return not any(f['quote'] in passage['text'] and f['page'] == passage['page'] for f in uncertain)


class KnowledgeService:
    def __init__(self, records, model, files, vault=None):
        self.records, self.model, self.files, self.vault = records, model, files, vault
        self.processing_key = f"{getattr(model, 'embedding_model', 'fixture')}:256:extraction-v1"

    def get(self, product_id):
        identifier(product_id)
        product = self.vault.get_product(product_id) if self.vault else {}
        initial = {}
        for native, field in [('modelNumber', 'product.model'), ('purchaseDate', 'product.purchaseDate'),
                              ('warrantyMonths', 'product.warrantyMonths'), ('warrantyExpiry', 'product.warrantyExpiry')]:
            if product.get(native) not in (None, ''):
                initial[field] = {'value': str(product[native]), 'source': {'type': 'product_record', 'id': product_id},
                                  'updatedAt': product.get('updatedAt', product.get('createdAt', ''))}
        return self.records.get('knowledge', product_id) or {
            'productId': product_id, 'schemaVersion': 1, 'revision': 0, 'facts': initial, 'conflicts': {}, 'changes': []}

    def merge_facts(self, product_id, facts, source, correction=False):
        self.get(product_id)
        if not all(is_product_field(field) for field in facts) or any(not isinstance(v, str) or not v.strip() or len(v) > 500 for v in facts.values()):
            raise ValueError('Unsupported reusable product fact')
        def update(previous):
            record = previous or self.get(product_id)
            changed = []
            for field, value in facts.items():
                entry = {'value': value.strip(), 'source': source, 'updatedAt': now()}
                old = record['facts'].get(field)
                if old and old['value'] != entry['value'] and not correction:
                    record['conflicts'][field] = entry
                    continue
                if not old or old['value'] != entry['value']:
                    record['facts'][field] = entry
                    changed.append(field)
                if correction:
                    record['conflicts'].pop(field, None)
            if changed:
                record['revision'] += 1
                record['changes'] = (record.get('changes', []) + [{'revision': record['revision'], 'fields': changed, 'facts': {field: record['facts'][field].copy() for field in changed}, 'source': source, 'createdAt': now()}])[-100:]
            return record
        return self.records.mutate('knowledge', product_id, update)

    def sync_product_fields(self, product, changed_fields):
        """Explicit product edits supersede learned values only for edited fields."""
        mapping = {'modelNumber': 'product.model', 'purchaseDate': 'product.purchaseDate',
                   'warrantyMonths': 'product.warrantyMonths', 'warrantyExpiry': 'product.warrantyExpiry'}
        selected = set(changed_fields)
        if selected & {'brandId', 'categoryId'}:
            selected.add('modelNumber')
        if selected & {'purchaseDate', 'warrantyMonths'}:
            selected.add('warrantyExpiry')
        fields = {field: product.get(native) for native, field in mapping.items() if native in selected}
        if selected & {'brandId', 'categoryId'}:
            brand = product.get('brandId')
            if self.vault and hasattr(self.vault, 'catalog'):
                category = next((c for c in self.vault.catalog()['categories'] if c['id'] == product.get('categoryId')), None)
                if category:
                    brand = next((b['name'] for b in category['brands'] if b['id'] == product.get('brandId')), brand)
            fields['product.brand'] = brand
        if not fields:
            return self.get(product['id'])
        source = {'type': 'product_record', 'id': product['id']}
        def update(previous):
            record = previous or self.get(product['id'])
            changed = []
            for field, value in fields.items():
                old = record['facts'].get(field)
                record['conflicts'].pop(field, None)
                if value in (None, ''):
                    if old:
                        record['facts'].pop(field); changed.append(field)
                elif not old or old['value'] != str(value):
                    record['facts'][field] = {'value': str(value), 'source': source, 'updatedAt': now()}
                    changed.append(field)
            if changed:
                record['revision'] += 1
                record['changes'] = (record.get('changes', []) + [{'revision': record['revision'],
                    'fields': changed, 'source': source, 'createdAt': now()}])[-100:]
            return record
        return self.records.mutate('knowledge', product['id'], update)

    def _source(self, product_id, document_id, case_id=None):
        identifier(document_id)
        metadata = self.files.metadata(document_id)
        allowed = (metadata['parentType'] == 'product' and metadata['parentId'] == product_id)
        saved = self.records.get('document_processing', document_id)
        allowed |= bool(saved and saved.get('productId') == product_id and saved.get('promoted'))
        if case_id:
            allowed |= metadata['parentType'] == 'case' and metadata['parentId'] == case_id
        if not allowed or metadata.get('status') != 'ready':
            raise ValueError('Document is outside this product or complaint')
        return metadata

    def document(self, product_id, document_id):
        self.get(product_id)
        result = self.records.get('document_processing', identifier(document_id))
        if not result or result.get('productId') != product_id:
            return None
        return {k: v for k, v in result.items() if k not in {'passages', 'extraction', 'lease'}}

    def documents(self, product_id):
        self.get(product_id)
        records = self.records.list_for_product(product_id) if hasattr(self.records, 'list_for_product') else self.records.list('document_processing')
        return [self.document(product_id, d['id']) for d in records if d.get('productId') == product_id]

    def _read(self, document_id):
        metadata, stream = self.files.open(document_id)
        with stream:
            return metadata, stream.read(5_000_001)

    async def ingest(self, product_id, document_id, case_id=None):
        await asyncio.to_thread(self.get, product_id)
        metadata = await asyncio.to_thread(self._source, product_id, document_id, case_id)
        _, data = await asyncio.to_thread(self._read, document_id)
        if len(data) > 5_000_000:
            raise ValueError('Document exceeds processing limit')
        version = hashlib.sha256(data).hexdigest()
        saved = await asyncio.to_thread(self.records.get, 'document_processing', document_id)
        if saved and saved.get('productId') == product_id and saved.get('version') == version and saved.get('processingKey') == self.processing_key:
            # Repeated upload callbacks do not spend another model call, including failures.
            return await asyncio.to_thread(self.document, product_id, document_id)
        active = await asyncio.to_thread(self.records.get, 'evidence', product_id) or {'documents': {}}
        duplicate_id = next((key for key, value in active['documents'].items() if value['version'] == version and value.get('processingKey') == self.processing_key), None)
        if duplicate_id and duplicate_id != document_id:
            canonical = await asyncio.to_thread(self.records.get, 'document_processing', duplicate_id)
            if canonical and canonical.get('processingStatus') == 'searchable':
                duplicate = {**metadata, 'productId': product_id, 'version': version,
                    'processingStatus': 'searchable', 'documentType': canonical['documentType'],
                    'description': canonical.get('description', ''), 'duplicateOf': duplicate_id,
                    'promoted': bool(case_id), 'processingKey': self.processing_key, 'updatedAt': now()}
                await asyncio.to_thread(self.records.mutate, 'document_processing', document_id, lambda _: duplicate)
                return duplicate
        import secrets
        lease = secrets.token_hex(16)
        record = {**metadata, 'productId': product_id, 'version': version,
                  'processingStatus': 'processing', 'updatedAt': now(), 'lease': lease, 'promoted': bool(case_id), 'processingKey': self.processing_key}
        def claim(previous):
            if previous and previous.get('processingStatus') == 'processing':
                raise ValueError('This document is already being processed')
            return record
        await asyncio.to_thread(self.records.mutate, 'document_processing', document_id, claim)
        try:
            async with asyncio.timeout(45):
                cached = await asyncio.to_thread(self.records.get, 'document_inspection', document_id)
                if (cached and cached.get('productId') == product_id and cached.get('caseId') == case_id
                    and cached.get('version') == version and cached.get('processingKey') == self.processing_key
                    and cached.get('extraction', {}).get('complete_for_product')):
                    extraction = Extraction.model_validate(cached['extraction'])
                else:
                    extraction = Extraction.model_validate(await self.model.extract(data, metadata['mediaType'],
                        {'product': await asyncio.to_thread(self.vault.get_product, product_id) if self.vault else {'id': product_id}}))
                if not extraction.product_match or extraction.document_type in {'unrelated', 'unknown'}:
                    return await asyncio.to_thread(self._finish, document_id, lease, {'processingStatus': 'not_indexable',
                        'documentType': extraction.document_type, 'description': extraction.description})
                passages = [p.model_dump() for p in extraction.passages]
                if not passages:
                    passages = [{'text': extraction.description, 'page': 1}] if extraction.description else []
                if not passages:
                    raise ValueError('No supported source content')
                for passage in passages:
                    passage['reviewRequired'] = not passage_is_certain(passage, [f.model_dump() for f in extraction.facts], passages)
                vectors = await self.model.embed([p['text'] for p in passages])
                if len(vectors) != len(passages):
                    raise ValueError('Incomplete document embeddings')
                for index, (p, vector) in enumerate(zip(passages, vectors)):
                    cosine(vector, vector)
                    p.update(id=f'{document_id}:{version[:12]}:{index}', documentId=document_id,
                             version=version, productId=product_id, vector=vector)
                def publish(previous):
                    result = previous or {'productId': product_id, 'documents': {}}
                    count = sum(len(v['passages']) for k, v in result['documents'].items() if k != document_id)
                    if count + len(passages) > 128:
                        raise ValueError('Product evidence limit reached; enter the needed fact instead')
                    result['documents'][document_id] = {'version': version, 'passages': passages, 'processingKey': self.processing_key}
                    return result
                # A single transaction replaces the active document version, never a partial index.
                await asyncio.to_thread(self.records.mutate, 'evidence', product_id, publish)
                for fact in extraction.facts:
                    if (is_product_field(fact.field) and not fact.uncertain
                            and any(fact.page == p['page'] and fact.quote in p['text'] for p in passages)):
                        await asyncio.to_thread(self.merge_facts, product_id, {fact.field: fact.value}, {'type': 'document', 'id': document_id,
                            'version': version, 'page': fact.page, 'quote': fact.quote})
                return await asyncio.to_thread(self._finish, document_id, lease, {'processingStatus': 'searchable',
                    'documentType': extraction.document_type, 'description': extraction.description,
                    'reviewRequired': any(f.uncertain for f in extraction.facts)})
        except Exception:
            await asyncio.to_thread(self._finish, document_id, lease, {'processingStatus': 'failed',
                'processingError': 'Could not prepare this document. You can supply the needed details in chat.'})
            return await asyncio.to_thread(self.document, product_id, document_id)

    def _finish(self, document_id, lease, changes):
        def update(record):
            if record.get('lease') != lease:
                raise ValueError('Document processing changed')
            return {**record, **changes, 'lease': None, 'updatedAt': now()}
        result = self.records.mutate('document_processing', document_id, update)
        return {k: v for k, v in result.items() if k not in {'lease', 'extraction', 'passages'}}

    async def search(self, product_id, question):
        await asyncio.to_thread(self.get, product_id)
        index = await asyncio.to_thread(self.records.get, 'evidence', product_id) or {'documents': {}}
        candidates = []
        for doc_id, doc in index['documents'].items():
            metadata = await asyncio.to_thread(self.records.get, 'document_processing', doc_id)
            if (metadata and metadata.get('processingStatus') == 'searchable' and metadata.get('version') == doc['version']
                and doc.get('processingKey') == self.processing_key):
                candidates.extend(p for p in doc['passages'] if not p.get('reviewRequired'))
        if not candidates:
            return []
        query = (await self.model.embed([question], query=True))[0]
        ranked = sorted(((cosine(query, p['vector']), p) for p in candidates), key=lambda x: x[0], reverse=True)
        return [{k: v for k, v in p.items() if k != 'vector'} for score, p in ranked[:6] if score >= .3]

    async def inspect_chat(self, case, document_id, question):
        await asyncio.to_thread(self._source, case['productId'], document_id, case['id'])
        metadata, data = await asyncio.to_thread(self._read, document_id)
        if len(data) > 5_000_000:
            raise ValueError('Document exceeds processing limit')
        result = Extraction.model_validate(await self.model.extract(data, metadata['mediaType'], {
            'product': case.get('factsSnapshot', {}).get('product', {}), 'question': question}))
        # Cached inspection is complaint-scoped; it is not a product search index.
        await asyncio.to_thread(self.records.mutate, 'document_inspection', document_id, lambda _: {
            'caseId': case['id'], 'productId': case['productId'], 'version': hashlib.sha256(data).hexdigest(),
            'processingKey': self.processing_key, 'extraction': result.model_dump()})
        return result.model_dump()

    async def promote(self, case, document_id):
        await asyncio.to_thread(self._source, case['productId'], document_id, case['id'])
        return await self.ingest(case['productId'], document_id, case['id'])
