"""API request/response schemas (provider-neutral, serializable)."""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.models import ParsedDocument


class DocumentOut(BaseModel):
    """Public view of a persisted document row."""

    id: str
    org_id: str
    owner_id: str
    filename: str
    mime_type: str
    checksum: str
    storage_uri: str
    status: str


class UploadResponse(BaseModel):
    """Result of a synchronous upload + parse + index (Phases 2-3)."""

    document: DocumentOut
    deduped: bool
    chunk_count: int = 0
    parsed: ParsedDocument | None = None


class SearchHit(BaseModel):
    """One raw similarity-search result."""

    chunk_id: str
    document_id: str
    text: str
    score: float
    page: int | None = None
    heading_path: str | None = None


class SearchResponse(BaseModel):
    """Raw dense similarity-search results (Phase 3; hybrid arrives in Phase 5)."""

    query: str
    hits: list[SearchHit]
