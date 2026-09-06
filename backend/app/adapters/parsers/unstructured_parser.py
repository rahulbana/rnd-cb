"""Unstructured parser -- alternate pipeline / second opinion.

Mature partitioning logic, useful for email (.eml), HTML, and Office formats,
or when Docling mis-segments a specific template family. Heavy import is lazy.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from app.domain.models import ParsedDocument, TextBlock

if TYPE_CHECKING:
    from app.core.config import Settings

_MIME_TYPES = {
    "message/rfc822",
    "text/html",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class UnstructuredParser:
    """Partitions a document into elements via the ``unstructured`` library."""

    name = "unstructured"

    @classmethod
    def from_settings(cls, settings: Settings) -> UnstructuredParser:
        return cls()

    def supports(self, mime_type: str) -> bool:
        return mime_type in _MIME_TYPES

    async def parse(
        self, data: bytes, *, filename: str, mime_type: str
    ) -> ParsedDocument:
        from unstructured.partition.auto import partition  # lazy import

        suffix = Path(filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(data)
            tmp.flush()
            elements = partition(filename=tmp.name)

        blocks: list[TextBlock] = []
        for element in elements:
            text = str(element).strip()
            if not text:
                continue
            page = None
            metadata = getattr(element, "metadata", None)
            if metadata is not None:
                page = getattr(metadata, "page_number", None)
            category = type(element).__name__
            heading = text if category in {"Title", "Header"} else None
            blocks.append(TextBlock(text=text, page=page, heading_path=heading))

        return ParsedDocument(
            source_filename=filename,
            mime_type=mime_type,
            text_blocks=blocks,
            page_count=max((b.page or 1) for b in blocks) if blocks else 1,
            parser_name=self.name,
        )
