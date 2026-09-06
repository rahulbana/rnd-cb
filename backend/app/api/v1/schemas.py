"""API request/response schemas (provider-neutral, serializable)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    org_id: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyCreateRequest(BaseModel):
    scopes: str = ""


class ApiKeyOut(BaseModel):
    id: str
    scopes: str
    last_used_at: str | None = None


class ApiKeyCreatedResponse(ApiKeyOut):
    api_key: str  # shown once


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


class ChatRequest(BaseModel):
    """A chat turn."""

    question: str
    conversation_id: str | None = None


class CitationOut(BaseModel):
    chunk_id: str
    document_id: str
    page: int | None = None
    heading_path: str | None = None
    score: float | None = None


class ChatResponse(BaseModel):
    """A grounded, cited answer plus its cost/latency trail."""

    conversation_id: str
    answer: str
    citations: list[CitationOut]
    provider: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cost_usd: float
    prompt_version: str
    found: bool


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    provider: str | None = None
    citations: list[CitationOut] = []
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0


class ConversationOut(BaseModel):
    id: str
    title: str


# --- Phase 9: admin, analytics, feedback, eval, trace ---


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int  # +1 or -1
    note: str | None = None


class ProviderCostOut(BaseModel):
    provider: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


class AnalyticsResponse(BaseModel):
    conversations: int
    messages: int
    tokens_in: int
    tokens_out: int
    cost_by_provider: list[ProviderCostOut]
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    top_documents: list[dict]
    feedback_up: int
    feedback_down: int


class QueueMonitorResponse(BaseModel):
    by_status: dict[str, int]
    by_stage: dict[str, int]


class AdminUserOut(BaseModel):
    id: str
    email: str
    role: str
    org_id: str


class ReprocessResponse(BaseModel):
    document_id: str
    job: JobOut


class TraceResponse(BaseModel):
    """Explains an answer: prompt version, provider, cost, and cited chunks."""

    message_id: str
    role: str
    provider: str | None
    prompt_version: str | None
    tokens_in: int
    tokens_out: int
    latency_ms: int
    citations: list[CitationOut]
