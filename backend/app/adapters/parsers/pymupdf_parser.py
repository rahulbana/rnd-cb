"""PyMuPDF (fitz) parser -- fast path for text-heavy, digitally-native PDFs.

Orders of magnitude faster than layout-aware parsing when a document has no
tables or complex layout worth preserving. The heavy import is lazy so the
skeleton boots (and unrelated tests run) without the library installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models import ParsedDocument, TextBlock

if TYPE_CHECKING:
    from app.core.config import Settings

_MIME_TYPES = {"application/pdf"}


class PyMuPDFParser:
    """Extracts text per page from a PDF using PyMuPDF."""

    name = "pymupdf"

    @classmethod
    def from_settings(cls, settings: Settings) -> PyMuPDFParser:
        return cls()

    def supports(self, mime_type: str) -> bool:
        return mime_type in _MIME_TYPES

    async def parse(
        self, data: bytes, *, filename: str, mime_type: str
    ) -> ParsedDocument:
        import pymupdf  # lazy: only needed when actually parsing a PDF

        blocks: list[TextBlock] = []
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            page_count = doc.page_count
            for page_index in range(page_count):
                page = doc[page_index]
                for block in page.get_text("blocks"):
                    # block = (x0, y0, x1, y1, text, block_no, block_type)
                    text = block[4].strip()
                    if text:
                        blocks.append(TextBlock(text=text, page=page_index + 1))

        return ParsedDocument(
            source_filename=filename,
            mime_type=mime_type,
            text_blocks=blocks,
            page_count=page_count,
            parser_name=self.name,
        )
