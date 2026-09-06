"""Per-format parser adapter tests against generated fixtures."""

from __future__ import annotations

import pytest

from app.adapters.parsers import (
    DocxParser,
    PlainTextParser,
    PyMuPDFParser,
    TesseractImageParser,
)
from app.domain.models import ParsedDocument
from tests import fixtures
from tests.conftest import requires_tesseract


@pytest.mark.asyncio
async def test_plaintext_markdown_keeps_headings():
    parser = PlainTextParser()
    parsed = await parser.parse(
        fixtures.make_markdown(title="Intro", body="hello markdown world"),
        filename="doc.md",
        mime_type="text/markdown",
    )
    assert isinstance(parsed, ParsedDocument)
    assert parsed.parser_name == "plain"
    assert "hello markdown world" in parsed.full_text
    # The heading was captured and propagated to following blocks.
    assert any(b.heading_path == "Intro" for b in parsed.text_blocks)


@pytest.mark.asyncio
async def test_pymupdf_extracts_pdf_text():
    parser = PyMuPDFParser()
    parsed = await parser.parse(
        fixtures.make_pdf("hello pdf world"),
        filename="doc.pdf",
        mime_type="application/pdf",
    )
    assert parsed.parser_name == "pymupdf"
    assert parsed.page_count == 1
    assert "hello pdf world" in parsed.full_text


@pytest.mark.asyncio
async def test_docx_extracts_text_and_tables():
    parser = DocxParser()
    parsed = await parser.parse(
        fixtures.make_docx(heading="Section One", body="hello docx world"),
        filename="doc.docx",
        mime_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    assert parsed.parser_name == "docx"
    assert "hello docx world" in parsed.full_text
    assert any(b.heading_path == "Section One" for b in parsed.text_blocks)
    assert parsed.tables and parsed.tables[0].rows[0] == ["k", "v"]


@requires_tesseract
@pytest.mark.asyncio
async def test_tesseract_ocrs_scanned_image():
    parser = TesseractImageParser()
    parsed = await parser.parse(
        fixtures.make_scanned_png("SCANNED DOCUMENT"),
        filename="scan.png",
        mime_type="image/png",
    )
    assert parsed.parser_name == "tesseract_image"
    text = parsed.full_text.upper()
    # OCR is noisy; assert a distinctive token survives.
    assert "SCANNED" in text or "DOCUMENT" in text
    assert parsed.image_refs == ["scan.png"]


def test_supports_mime_routing():
    assert PlainTextParser().supports("text/markdown")
    assert not PlainTextParser().supports("application/pdf")
    assert PyMuPDFParser().supports("application/pdf")
    assert TesseractImageParser().supports("image/png")


@pytest.mark.asyncio
async def test_all_formats_return_same_canonical_shape():
    """Every parser returns the identical ParsedDocument top-level shape."""
    md = await PlainTextParser().parse(
        fixtures.make_markdown(), filename="a.md", mime_type="text/markdown"
    )
    pdf = await PyMuPDFParser().parse(
        fixtures.make_pdf(), filename="a.pdf", mime_type="application/pdf"
    )
    docx = await DocxParser().parse(
        fixtures.make_docx(),
        filename="a.docx",
        mime_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    keys = set(md.model_dump())
    assert set(pdf.model_dump()) == keys
    assert set(docx.model_dump()) == keys
    assert all(p.text_blocks for p in (md, pdf, docx))
