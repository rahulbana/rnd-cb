"""Async upload: acceptance, dedup, rate limit, and end-to-end ingest+search."""

from __future__ import annotations

from tests import fixtures
from tests.conftest import requires_tesseract

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _upload(client, name, data, content_type):
    return client.post(
        "/api/v1/documents",
        files={"file": (name, data, content_type)},
    )


def test_upload_accepted_and_indexed_inline(upload_client):
    resp = _upload(upload_client, "notes.md", fixtures.make_markdown(), "text/markdown")
    assert resp.status_code == 202
    body = resp.json()
    assert body["deduped"] is False
    # Inline queue completes the job before the response returns.
    assert body["job"]["status"] == "completed"
    assert body["job"]["progress"] == 100
    assert body["document"]["status"] == "indexed"


def test_upload_then_search_end_to_end(upload_client):
    """Phase 3 exit still holds through the async path: ingested and retrievable."""
    body_text = "the mitochondria is the powerhouse of the cell"
    up = _upload(
        upload_client, "bio.md", fixtures.make_markdown(body=body_text), "text/markdown"
    )
    assert up.status_code == 202
    assert up.json()["job"]["status"] == "completed"

    resp = upload_client.post(
        "/api/v1/documents/search", params={"q": body_text, "top_k": 3}
    )
    assert resp.status_code == 200
    hits = resp.json()["hits"]
    assert hits
    assert any("mitochondria" in h["text"] for h in hits)
    assert hits[0]["document_id"] == up.json()["document"]["id"]


def test_dedup_by_checksum(upload_client):
    data = fixtures.make_markdown(body="dedup me")
    first = _upload(upload_client, "a.md", data, "text/markdown")
    second = _upload(upload_client, "a.md", data, "text/markdown")
    assert first.status_code == 202 and second.status_code == 202
    assert first.json()["deduped"] is False
    assert second.json()["deduped"] is True
    assert second.json()["job"] is None
    assert first.json()["document"]["id"] == second.json()["document"]["id"]
    assert len(upload_client.get("/api/v1/documents").json()) == 1


def test_empty_upload_rejected(upload_client):
    resp = _upload(upload_client, "empty.md", b"", "text/markdown")
    assert resp.status_code == 400


def test_rate_limit_returns_429(async_env, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "INGEST_RATE_LIMIT", 2)
    client = async_env("inline")
    ok1 = _upload(client, "a.md", fixtures.make_markdown(body="one"), "text/markdown")
    ok2 = _upload(client, "b.md", fixtures.make_markdown(body="two"), "text/markdown")
    blocked = _upload(
        client, "c.md", fixtures.make_markdown(body="three"), "text/markdown"
    )
    assert ok1.status_code == 202 and ok2.status_code == 202
    assert blocked.status_code == 429


def test_pdf_ingests_and_is_searchable(upload_client):
    up = _upload(
        upload_client, "d.pdf", fixtures.make_pdf("hello pdf world"), "application/pdf"
    )
    assert up.status_code == 202
    assert up.json()["job"]["status"] == "completed"
    hits = upload_client.post(
        "/api/v1/documents/search", params={"q": "hello pdf world"}
    ).json()["hits"]
    assert any("pdf" in h["text"] for h in hits)


def test_docx_ingests(upload_client):
    up = _upload(upload_client, "d.docx", fixtures.make_docx(), _DOCX_MIME)
    assert up.status_code == 202
    assert up.json()["job"]["status"] == "completed"
    assert up.json()["document"]["status"] == "indexed"


@requires_tesseract
def test_scanned_png_ingests(upload_client):
    up = _upload(
        upload_client, "scan.png", fixtures.make_scanned_png("SCANNED"), "image/png"
    )
    assert up.status_code == 202
    assert up.json()["job"]["status"] == "completed"
