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
    """Result of a synchronous upload + parse (Phase 2)."""

    document: DocumentOut
    deduped: bool
    parsed: ParsedDocument | None = None
