"""Upload endpoint: dedup, per-format parsing, and the Phase 2 exit test."""

from __future__ import annotations

from tests import fixtures
from tests.conftest import requires_tesseract

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# The canonical top-level shape every parser must return.
_PARSED_KEYS = {
    "source_filename",
    "mime_type",
    "text_blocks",
    "tables",
    "image_refs",
    "page_count",
    "parser_name",
    "used_fallback",
}


def _upload(client, name, data, content_type):
    return client.post(
        "/api/v1/documents",
        files={"file": (name, data, content_type)},
    )


def test_upload_markdown_parses(upload_client):
    resp = _upload(upload_client, "notes.md", fixtures.make_markdown(), "text/markdown")
    assert resp.status_code == 201
    body = resp.json()
    assert body["deduped"] is False
    assert body["document"]["status"] == "parsed"
    assert body["parsed"]["parser_name"] == "plain"
    assert set(body["parsed"]) == _PARSED_KEYS


def test_upload_pdf_parses(upload_client):
    resp = _upload(
        upload_client, "doc.pdf", fixtures.make_pdf("hello pdf world"), "application/pdf"
    )
    assert resp.status_code == 201
    parsed = resp.json()["parsed"]
    assert parsed["parser_name"] == "pymupdf"
    assert "hello pdf world" in "\n".join(b["text"] for b in parsed["text_blocks"])


def test_upload_docx_parses(upload_client):
    resp = _upload(upload_client, "doc.docx", fixtures.make_docx(), _DOCX_MIME)
    assert resp.status_code == 201
    parsed = resp.json()["parsed"]
    assert parsed["parser_name"] == "docx"
    assert "hello docx world" in "\n".join(b["text"] for b in parsed["text_blocks"])


def test_upload_dedup_by_checksum(upload_client):
    data = fixtures.make_markdown(body="dedup me")
    first = _upload(upload_client, "a.md", data, "text/markdown")
    second = _upload(upload_client, "a.md", data, "text/markdown")
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["deduped"] is False
    assert second.json()["deduped"] is True
    # Same content -> same stored document, not a duplicate row.
    assert first.json()["document"]["id"] == second.json()["document"]["id"]
    listing = upload_client.get("/api/v1/documents").json()
    assert len(listing) == 1


def test_empty_upload_rejected(upload_client):
    resp = _upload(upload_client, "empty.md", b"", "text/markdown")
    assert resp.status_code == 400


@requires_tesseract
def test_upload_scanned_png_parses(upload_client):
    resp = _upload(
        upload_client,
        "scan.png",
        fixtures.make_scanned_png("SCANNED DOCUMENT"),
        "image/png",
    )
    assert resp.status_code == 201
    parsed = resp.json()["parsed"]
    assert parsed["parser_name"] == "tesseract_image"
    text = "\n".join(b["text"] for b in parsed["text_blocks"]).upper()
    assert "SCANNED" in text or "DOCUMENT" in text


@requires_tesseract
def test_exit_all_formats_return_same_shape(upload_client):
    """Phase 2 exit: PDF, DOCX, scanned PNG, and Markdown all upload and
    return the same canonical structured representation."""
    cases = [
        ("doc.pdf", fixtures.make_pdf("pdf body"), "application/pdf", "pymupdf"),
        ("doc.docx", fixtures.make_docx(), _DOCX_MIME, "docx"),
        (
            "scan.png",
            fixtures.make_scanned_png("SCANNED"),
            "image/png",
            "tesseract_image",
        ),
        ("notes.md", fixtures.make_markdown(), "text/markdown", "plain"),
    ]
    for name, data, content_type, expected_parser in cases:
        resp = _upload(upload_client, name, data, content_type)
        assert resp.status_code == 201, name
        parsed = resp.json()["parsed"]
        # Identical top-level shape regardless of source format.
        assert set(parsed) == _PARSED_KEYS, name
        assert parsed["parser_name"] == expected_parser, name
        assert parsed["text_blocks"], name
