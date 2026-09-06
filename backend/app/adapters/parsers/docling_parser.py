"""Docling parser -- the production primary for nearly everything.

Handles PDF, DOCX, PPTX, HTML, images and scanned pages (built-in OCR),
preserving layout and table structure, fully local. The import is heavy
(ML stack) so it is lazy: the app and unrelated tests run without Docling
installed; only ``parse`` pulls it in.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from app.domain.models import ParsedDocument, TextBlock

if TYPE_CHECKING:
    from app.core.config import Settings

# Docling covers the broad set of formats; images trigger its OCR path.
_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/html",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/bmp",
}


class DoclingParser:
    """Layout- and table-aware parsing via Docling, with OCR for images."""

    name = "docling"

    @classmethod
    def from_settings(cls, settings: Settings) -> DoclingParser:
        return cls()

    def supports(self, mime_type: str) -> bool:
        return mime_type in _MIME_TYPES

    async def parse(
        self, data: bytes, *, filename: str, mime_type: str
    ) -> ParsedDocument:
        from docling.document_converter import DocumentConverter  # lazy import

        suffix = Path(filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(data)
            tmp.flush()
            converter = DocumentConverter()
            result = converter.convert(tmp.name)

        doc = result.document
        markdown = doc.export_to_markdown()
        blocks = [
            TextBlock(text=line.strip()) for line in markdown.splitlines() if line.strip()
        ]

        page_count = len(getattr(doc, "pages", []) or []) or 1
        return ParsedDocument(
            source_filename=filename,
            mime_type=mime_type,
            text_blocks=blocks,
            page_count=page_count,
            parser_name=self.name,
        )
