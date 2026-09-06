"""Chunker port -- splits a ParsedDocument into retrievable chunks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.domain.models import Chunk, ParsedDocument

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class Chunker(Protocol):
    """Any chunking strategy must satisfy this."""

    name: str  # "structure_aware" | "fixed_size" | "recursive" | ...

    @classmethod
    def from_settings(cls, settings: Settings) -> Chunker:
        """Construct the adapter from application settings."""
        ...

    def chunk(self, document: ParsedDocument, *, document_id: str) -> list[Chunk]:
        """Split a parsed document into chunks."""
        ...
