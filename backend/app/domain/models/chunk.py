"""Chunk domain model produced by the chunker port."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Citation-relevant metadata carried alongside every chunk."""

    document_id: str
    page: int | None = None
    heading_path: str | None = None
    ordinal: int = 0


class Chunk(BaseModel):
    """A retrievable unit of text plus its provenance."""

    id: str
    text: str
    metadata: ChunkMetadata
    extra: dict[str, str] = Field(default_factory=dict)
