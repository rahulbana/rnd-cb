"""Fixed-size chunker -- naive character windows over the whole document."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.adapters.chunkers._textsplit import char_windows
from app.domain.models import Chunk, ChunkMetadata, ParsedDocument

if TYPE_CHECKING:
    from app.core.config import Settings


class FixedSizeChunker:
    """Splits the concatenated document text into fixed-size overlapping windows."""

    name = "fixed_size"

    def __init__(self, size: int = 800, overlap: int = 120) -> None:
        self.size = size
        self.overlap = overlap

    @classmethod
    def from_settings(cls, settings: Settings) -> FixedSizeChunker:
        return cls(size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)

    def chunk(self, document: ParsedDocument, *, document_id: str) -> list[Chunk]:
        windows = char_windows(document.full_text, self.size, self.overlap)
        return [
            Chunk(
                id=f"{document_id}:{ordinal}",
                text=window.strip(),
                metadata=ChunkMetadata(document_id=document_id, ordinal=ordinal),
            )
            for ordinal, window in enumerate(windows)
        ]
