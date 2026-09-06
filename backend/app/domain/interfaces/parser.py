"""Parser port -- turns raw bytes of any format into a ParsedDocument."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.domain.models import ParsedDocument

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class Parser(Protocol):
    """Any document parser must satisfy this."""

    name: str  # "docling" | "pymupdf" | "unstructured" | "plain" | ...

    @classmethod
    def from_settings(cls, settings: Settings) -> Parser:
        """Construct the adapter from application settings."""
        ...

    def supports(self, mime_type: str) -> bool:
        """Whether this parser can handle the given MIME type."""
        ...

    async def parse(
        self, data: bytes, *, filename: str, mime_type: str
    ) -> ParsedDocument:
        """Parse raw bytes into the canonical document shape."""
        ...
