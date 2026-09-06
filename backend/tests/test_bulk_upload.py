"""Bulk (zip) upload endpoint."""

from __future__ import annotations

import io
import zipfile

from tests import fixtures

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _post_zip(client, data: bytes):
    return client.post(
        "/api/v1/documents/bulk",
        files={"file": ("batch.zip", data, "application/zip")},
    )


def test_bulk_upload_ingests_all(upload_client):
    zip_bytes = _make_zip(
        {
            "a.md": fixtures.make_markdown(body="first doc"),
            "b.txt": fixtures.make_text("second doc body"),
            "c.pdf": fixtures.make_pdf("third doc body"),
            "d.docx": fixtures.make_docx(body="fourth doc body"),
        }
    )
    resp = _post_zip(upload_client, zip_bytes)
    assert resp.status_code == 202
    body = resp.json()
    assert body["accepted"] == 4
    # Inline queue -> each completed.
    for item in body["items"]:
        assert item["deduped"] is False
        assert item["job"]["status"] == "completed"
        assert item["document"]["status"] == "indexed"

    assert len(upload_client.get("/api/v1/documents").json()) == 4


def test_bulk_upload_rejects_non_zip(upload_client):
    assert _post_zip(upload_client, b"not a zip").status_code == 400


def test_bulk_upload_respects_max_docs(async_env, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_BULK_DOCS", 2)
    client = async_env("inline")
    zip_bytes = _make_zip(
        {f"f{i}.md": fixtures.make_markdown(body=f"doc {i}") for i in range(3)}
    )
    assert _post_zip(client, zip_bytes).status_code == 413
