"""In-memory fake parser -- decodes bytes as UTF-8 text, one block per line."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models import ParsedDocument, TextBlock

if TYPE_CHECKING:
    from app.core.config import Settings


class FakeParser:
    """Treats input as plain UTF-8 text; accepts any MIME type."""

    name = "fake"

    @classmethod
    def from_settings(cls, settings: Settings) -> FakeParser:
        return cls()

    def supports(self, mime_type: str) -> bool:
        return True

    async def parse(
        self, data: bytes, *, filename: str, mime_type: str
    ) -> ParsedDocument:
        text = data.decode("utf-8", errors="replace")
        blocks = [
            TextBlock(text=line, page=1) for line in text.splitlines() if line.strip()
        ]
        return ParsedDocument(
            source_filename=filename,
            mime_type=mime_type,
            text_blocks=blocks,
            page_count=1,
            parser_name=self.name,
        )
