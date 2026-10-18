"""Small transactional record boundary within the existing workspace."""
from app.services.repository import FirestoreVaultStore

class FirestoreRecords:
    KINDS = frozenset({'knowledge', 'evidence', 'document_processing', 'document_inspection', 'turns'})

    def __init__(self, project_id, namespace='shared'):
        self.vault = FirestoreVaultStore(project_id, namespace)

    def _ref(self, kind, key):
        if kind not in self.KINDS or not key or '/' in key:
            raise ValueError('Invalid knowledge record')
        return self.vault.root.collection(kind).document(key)

    def get(self, kind, key):
        snapshot = self._ref(kind, key).get(retry=None, timeout=5)
        return snapshot.to_dict() if snapshot.exists else None

    def mutate(self, kind, key, fn):
        from google.cloud import firestore
        ref = self._ref(kind, key)
        @firestore.transactional
        def apply(transaction):
            snapshot = ref.get(transaction=transaction)
            value = fn(snapshot.to_dict() if snapshot.exists else None)
            transaction.set(ref, value)
            return value
        return apply(self.vault.client.transaction())

    def list_for_product(self, product_id):
        from google.cloud.firestore_v1.base_query import FieldFilter
        return [s.to_dict() for s in self.vault.root.collection('document_processing').where(
            filter=FieldFilter('productId', '==', product_id)).limit(64).stream(timeout=5)]
