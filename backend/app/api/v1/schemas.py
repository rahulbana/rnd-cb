"""API request/response schemas (provider-neutral, serializable)."""

from __future__ import annotations

from pydantic import BaseModel


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


class JobOut(BaseModel):
    """Ingestion job status -- observable mid-flight."""

    id: str
    document_id: str
    stage: str
    progress: int
    status: str
    error: str | None = None
    retries: int = 0


class IngestAcceptedResponse(BaseModel):
    """Result of an async upload: the job is accepted and enqueued."""

    document: DocumentOut
    job: JobOut | None = None
    deduped: bool


class BulkItem(BaseModel):
    """One entry's outcome within a bulk (zip) upload."""

    filename: str
    document: DocumentOut | None = None
    job: JobOut | None = None
    deduped: bool = False
    error: str | None = None


class BulkIngestResponse(BaseModel):
    """Result of a bulk (zip) upload."""

    accepted: int
    items: list[BulkItem]


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


class RetrieveHit(BaseModel):
    """One retrieval result, tagged with which retriever surfaced it."""

    chunk_id: str
    document_id: str
    text: str
    score: float
    source: str
    page: int | None = None
    heading_path: str | None = None


class RetrieveFilters(BaseModel):
    year: int | None = None
    doc_type: str | None = None


class RetrieveResponse(BaseModel):
    """Standalone retrieval results (retrieval independent of generation)."""

    query: str
    strategy: str
    filters: RetrieveFilters
    scoped_document_count: int | None = None
    hits: list[RetrieveHit]
