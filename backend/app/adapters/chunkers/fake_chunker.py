"""In-memory fake chunker -- one chunk per text block."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models import Chunk, ChunkMetadata, ParsedDocument

if TYPE_CHECKING:
    from app.core.config import Settings


class FakeChunker:
    """Emits one chunk per non-empty text block, preserving provenance."""

    name = "fake"

    @classmethod
    def from_settings(cls, settings: Settings) -> FakeChunker:
        return cls()

    def chunk(self, document: ParsedDocument, *, document_id: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        for ordinal, block in enumerate(document.text_blocks):
            chunks.append(
                Chunk(
                    id=f"{document_id}:{ordinal}",
                    text=block.text,
                    metadata=ChunkMetadata(
                        document_id=document_id,
                        page=block.page,
                        heading_path=block.heading_path,
                        ordinal=ordinal,
                    ),
                )
            )
        return chunks
