"""Recursive chunker -- splits on a separator hierarchy toward a target size."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.adapters.chunkers._textsplit import recursive_split
from app.domain.models import Chunk, ChunkMetadata, ParsedDocument

if TYPE_CHECKING:
    from app.core.config import Settings


class RecursiveChunker:
    """Splits on paragraph/line/sentence/word boundaries, largest first."""

    name = "recursive"

    def __init__(self, size: int = 800, overlap: int = 120) -> None:
        self.size = size
        self.overlap = overlap

    @classmethod
    def from_settings(cls, settings: Settings) -> RecursiveChunker:
        return cls(size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)

    def chunk(self, document: ParsedDocument, *, document_id: str) -> list[Chunk]:
        pieces = recursive_split(document.full_text, self.size, self.overlap)
        return [
            Chunk(
                id=f"{document_id}:{ordinal}",
                text=piece.strip(),
                metadata=ChunkMetadata(document_id=document_id, ordinal=ordinal),
            )
            for ordinal, piece in enumerate(pieces)
        ]
