"""Durable simulator replay in its own Firestore namespace."""


class FirestoreReplayStore:
    def __init__(self, project_id: str, namespace: str = "shared"):
        self.project_id = project_id
        self.namespace = namespace
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google.cloud import firestore

            self._client = firestore.Client(project=self.project_id or None)
        return self._client

    @property
    def root(self):
        return self.client.collection("custra_business").document(self.namespace)

    def transact(self, operation_id, digest, case_id, generate):
        from google.cloud import firestore

        root = self.root
        operation_ref = root.collection("operations").document(operation_id)
        case_ref = root.collection("cases").document(case_id)

        @firestore.transactional
        def apply(transaction):
            previous = operation_ref.get(transaction=transaction)
            if previous.exists:
                saved = previous.to_dict()
                if saved["payloadHash"] != digest:
                    raise ValueError("Operation payload changed")
                return saved["response"]
            snapshot = case_ref.get(transaction=transaction)
            response, updated = generate(snapshot.to_dict() if snapshot.exists else {})
            transaction.set(case_ref, updated)
            transaction.create(operation_ref, {"payloadHash": digest, "response": response})
            return response

        return apply(self.client.transaction())
