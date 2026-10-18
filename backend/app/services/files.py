"""Bounded private document upload and authenticated viewing."""

import io
import hashlib
import os
import uuid
from datetime import datetime, timezone


MAX_BYTES = 5_000_000
SUPPORTED = {
    "application/pdf": (b"%PDF-", {".pdf"}),
    "image/jpeg": (b"\xff\xd8\xff", {".jpg", ".jpeg"}),
    "image/png": (b"\x89PNG\r\n\x1a\n", {".png"}),
}


class CloudBucket:
    def __init__(self, project_id: str, bucket_name: str):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self._bucket = None

    def blob(self, key: str):
        if not self.bucket_name:
            raise RuntimeError("Private document bucket is not configured")
        if self._bucket is None:
            from google.cloud import storage

            self._bucket = storage.Client(project=self.project_id or None).bucket(self.bucket_name)
        return self._bucket.blob(key)


class FileService:
    def __init__(self, bucket, store):
        self.bucket = bucket
        self.store = store

    def upload(self, parent_type: str, parent_id: str, filename: str, stream,
               media_type: str) -> dict:
        if parent_type not in {"product", "case"} or not parent_id:
            raise ValueError("Invalid document parent")
        original_name = os.path.basename(filename.replace("\\", "/")).strip()
        if not original_name or len(original_name) > 180 or media_type not in SUPPORTED:
            raise ValueError("Only PDF, JPEG and PNG files are allowed")
        signature, extensions = SUPPORTED[media_type]
        if os.path.splitext(original_name)[1].lower() not in extensions:
            raise ValueError("File name does not match its media type")
        data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("File exceeds 5,000,000 bytes")
        if not data.startswith(signature):
            raise ValueError("File content does not match its media type")

        document_id = uuid.uuid4().hex
        object_key = f"documents/{uuid.uuid4().hex}"
        record = {
            "id": document_id, "parentType": parent_type, "parentId": parent_id,
            "objectKey": object_key, "originalName": original_name,
            "mediaType": media_type, "size": len(data), "status": "pending",
            "createdAt": datetime.now(timezone.utc).isoformat(), "version": hashlib.sha256(data).hexdigest(),
        }
        self.store.save(record)
        blob = None
        try:
            blob = self.bucket.blob(object_key)
            blob.upload_from_file(io.BytesIO(data), content_type=media_type)
            record["status"] = "ready"
            self.store.save(record)
        except Exception:
            record["status"] = "failed"
            try:
                self.store.save(record)
            finally:
                if blob is not None:
                    try:
                        blob.delete()
                    except Exception:
                        pass
            raise
        return record

    def list_for_parent(self, parent_type: str, parent_id: str) -> list[dict]:
        return self.store.list_for_parent(parent_type, parent_id)

    def metadata(self, document_id: str):
        record = self.store.get(document_id)
        if not record or record.get("status") != "ready":
            raise LookupError("Document not found")
        return record

    def open(self, document_id: str):
        record = self.store.get(document_id)
        if not record or record.get("status") != "ready":
            raise LookupError("Document not found")
        return record, self.bucket.blob(record["objectKey"]).open("rb")
