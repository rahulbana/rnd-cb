"""Structure-aware chunker (default).

Respects document structure: text blocks are grouped by their heading path and
packed toward the target size, splitting further only when a group overflows.
Tables become their own chunks. Page and heading provenance is carried into
each chunk's metadata so citations (Phase 6) can point back to source.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.adapters.chunkers._textsplit import recursive_split
from app.domain.models import Chunk, ChunkMetadata, ParsedDocument, TableBlock, TextBlock

if TYPE_CHECKING:
    from app.core.config import Settings


def _table_to_text(table: TableBlock) -> str:
    return "\n".join(" | ".join(cell for cell in row) for row in table.rows)


class StructureAwareChunker:
    """Groups blocks by heading, packs to size, and keeps tables intact."""

    name = "structure_aware"

    def __init__(self, size: int = 800, overlap: int = 120) -> None:
        self.size = size
        self.overlap = overlap

    @classmethod
    def from_settings(cls, settings: Settings) -> StructureAwareChunker:
        return cls(size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)

    def chunk(self, document: ParsedDocument, *, document_id: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        counter = 0

        def emit(text: str, page: int | None, heading: str | None) -> None:
            nonlocal counter
            text = text.strip()
            if not text:
                return
            chunks.append(
                Chunk(
                    id=f"{document_id}:{counter}",
                    text=text,
                    metadata=ChunkMetadata(
                        document_id=document_id,
                        page=page,
                        heading_path=heading,
                        ordinal=counter,
                    ),
                )
            )
            counter += 1

        # Group contiguous text blocks sharing a heading path.
        group: list[TextBlock] = []

        def flush_group() -> None:
            if not group:
                return
            heading = group[0].heading_path
            page = group[0].page
            body = "\n\n".join(b.text for b in group)
            if len(body) <= self.size:
                emit(body, page, heading)
            else:
                for piece in recursive_split(body, self.size, self.overlap):
                    emit(piece, page, heading)
            group.clear()

        current_heading: str | None = None
        for block in document.text_blocks:
            if block.heading_path != current_heading and group:
                flush_group()
            current_heading = block.heading_path
            group.append(block)
        flush_group()

        # Tables are standalone chunks.
        for table in document.tables:
            emit(_table_to_text(table), table.page, table.caption)

        return chunks
