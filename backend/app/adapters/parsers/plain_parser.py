"""Plain text / Markdown loader.

Trivial formats (.txt, .md) need no parsing. Markdown headings are preserved
as ``heading_path`` so structure-aware chunking (Phase 3) can use them as
chunk boundaries.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.domain.models import ParsedDocument, TextBlock

if TYPE_CHECKING:
    from app.core.config import Settings

_MIME_TYPES = {"text/plain", "text/markdown", "text/x-markdown"}
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


class PlainTextParser:
    """Reads UTF-8 text; keeps Markdown heading structure."""

    name = "plain"

    @classmethod
    def from_settings(cls, settings: Settings) -> PlainTextParser:
        return cls()

    def supports(self, mime_type: str) -> bool:
        return mime_type in _MIME_TYPES

    async def parse(
        self, data: bytes, *, filename: str, mime_type: str
    ) -> ParsedDocument:
        text = data.decode("utf-8", errors="replace")
        blocks: list[TextBlock] = []
        heading_path: str | None = None

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            match = _HEADING_RE.match(stripped)
            if match:
                heading_path = match.group(2).strip()
                blocks.append(
                    TextBlock(text=heading_path, page=1, heading_path=heading_path)
                )
            else:
                blocks.append(TextBlock(text=stripped, page=1, heading_path=heading_path))

        return ParsedDocument(
            source_filename=filename,
            mime_type=mime_type,
            text_blocks=blocks,
            page_count=1,
            parser_name=self.name,
        )
