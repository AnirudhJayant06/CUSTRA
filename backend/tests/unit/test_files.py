import io
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.main import create_app
from app.config import Settings
from app.services.auth import token_digest
from app.services.files import FileService


PDF = b"%PDF-1.7\nfictional document"
JPEG = b"\xff\xd8\xff\xe0fictional image"
PNG = b"\x89PNG\r\n\x1a\nfictional image"


class FakeDocuments:
    def __init__(self):
        self.rows = {}

    def save(self, record):
        self.rows[record["id"]] = record.copy()

    def get(self, id):
        return self.rows.get(id)

    def list_for_parent(self, parent_type, parent_id):
        return [row for row in self.rows.values() if row["parentType"] == parent_type
                and row["parentId"] == parent_id and row["status"] == "ready"]


class FakeBlob:
    def __init__(self, bucket, key):
        self.bucket = bucket
        self.key = key

    def upload_from_file(self, stream, content_type):
        if self.bucket.fail:
            raise OSError("fake upload failure")
        self.bucket.objects[self.key] = stream.read()

    def open(self, mode):
        assert mode == "rb"
        return io.BytesIO(self.bucket.objects[self.key])

    def delete(self):
        self.bucket.objects.pop(self.key, None)


class FakeBucket:
    def __init__(self, fail=False):
        self.fail = fail
        self.objects = {}

    def blob(self, key):
        return FakeBlob(self, key)


def test_rejects_oversize_or_disguised_file():
    bucket, store = FakeBucket(), FakeDocuments()
    files = FileService(bucket, store)
    with pytest.raises(ValueError):
        files.upload("product", "product-1", "large.pdf", io.BytesIO(PDF + b"x" * 5_000_000), "application/pdf")
    with pytest.raises(ValueError):
        files.upload("product", "product-1", "fake.pdf", io.BytesIO(b"<html>not a PDF</html>"), "application/pdf")
    with pytest.raises(ValueError):
        files.upload("product", "product-1", "vector.svg", io.BytesIO(b"<svg></svg>"), "image/svg+xml")
    assert not bucket.objects and not store.rows
    for name, content, media_type in [("a.pdf", PDF, "application/pdf"),
                                      ("b.jpg", JPEG, "image/jpeg"), ("c.png", PNG, "image/png")]:
        saved = files.upload("product", "product-1", name, io.BytesIO(content), media_type)
        assert saved["status"] == "ready"
        assert bucket.objects[saved["objectKey"]] == content


def test_failed_upload_not_ready():
    bucket, store = FakeBucket(fail=True), FakeDocuments()
    files = FileService(bucket, store)
    with pytest.raises(OSError):
        files.upload("product", "product-1", "a.pdf", io.BytesIO(PDF), "application/pdf")
    assert len(store.rows) == 1
    record = next(iter(store.rows.values()))
    assert record["status"] == "failed"
    assert not bucket.objects
    with pytest.raises(LookupError):
        files.open(record["id"])


@pytest.mark.asyncio
async def test_download_requires_session():
    app = create_app(file_store=FakeDocuments(), file_bucket=FakeBucket())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://api.test") as client:
        response = await client.get("/api/documents/fictional-id/content")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_upload_request_has_a_bound_before_multipart_parsing():
    app = create_app(file_store=FakeDocuments(), file_bucket=FakeBucket())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://api.test") as client:
        response = await client.post("/api/products/fictional/documents", content=b"x" * 5_100_001)
    assert response.status_code == 413
    assert response.json()["code"] == "upload_too_large"


@pytest.mark.asyncio
async def test_authorized_document_upload_and_private_stream():
    class Sessions:
        def get(self, digest):
            if digest == token_digest("fictional-session"):
                return {"expires_at": datetime.now(timezone.utc) + timedelta(hours=1), "revoked": False}
            return None

    class Vault:
        def get_product(self, id):
            return {"id": id} if id == "product-1" else None

    store = FakeDocuments()
    app = create_app(settings=Settings(secure_cookies=False), session_store=Sessions(),
                     vault_store=Vault(), file_store=store, file_bucket=FakeBucket())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://api.test") as client:
        client.cookies.set("__session", "fictional-session")
        uploaded = await client.post("/api/products/product-1/documents",
                                     files={"file": ("invoice.pdf", PDF, "application/pdf")})
        assert uploaded.status_code == 200
        document_id = uploaded.json()["id"]
        listed = await client.get("/api/products/product-1/documents")
        assert [item["id"] for item in listed.json()] == [document_id]
        content = await client.get(f"/api/documents/{document_id}/content")
        assert content.status_code == 200
        assert content.content == PDF
        assert content.headers["x-content-type-options"] == "nosniff"
        assert content.headers["content-disposition"].startswith("attachment;")
        assert content.headers["cache-control"] == "private, no-store"


@pytest.mark.asyncio
async def test_case_documents_support_pdf_and_reject_uploads_after_closure():
    class Sessions:
        def get(self, digest):
            return {'expires_at': datetime.now(timezone.utc) + timedelta(hours=1), 'revoked': False}

    class Cases:
        status = 'BOOKED'
        def get(self, id): return {'id': id, 'status': self.status}

    records = FakeDocuments()
    app = create_app(settings=Settings(secure_cookies=False), session_store=Sessions(),
                     file_store=records, file_bucket=FakeBucket())
    app.state.cases = Cases()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://api.test') as client:
        client.cookies.set('__session', 'fictional-session')
        uploaded = await client.post('/api/complaints/case-1/documents', files={'file': ('invoice.pdf', PDF, 'application/pdf')})
        assert uploaded.status_code == 200
        app.state.cases.status = 'CLOSED'
        for name, content, mime in [('photo.png', PNG, 'image/png'), ('invoice.pdf', PDF, 'application/pdf')]:
            rejected = await client.post('/api/complaints/case-1/documents', files={'file': (name, content, mime)})
            assert rejected.status_code == 409
        assert len(records.rows) == 1
        assert (await client.get('/api/complaints/case-1/documents')).json()[0]['id'] == uploaded.json()['id']
        assert (await client.get(f"/api/documents/{uploaded.json()['id']}/content")).content == PDF
