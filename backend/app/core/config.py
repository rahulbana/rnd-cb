"""Application settings -- the single wiring diagram.

One ``.env`` value picks each implementation. Nothing in business logic is
hardcoded to a provider; only the registry reads these values.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    APP_NAME: str = "rag-platform"
    ENV: str = "dev"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # --- Security (single-tenant today, multi-tenant-shaped) ---
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    DEFAULT_ORG_ID: str = "00000000-0000-0000-0000-000000000000"
    # First registered user becomes an admin (single-org bootstrap).
    FIRST_USER_IS_ADMIN: bool = True

    # --- Datastores ---
    DATABASE_URL: str = "postgresql+psycopg://rag:rag@localhost:5432/rag"
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # --- Provider selection: the swappable core ---
    LLM_PROVIDER: str = Field(default="ollama")
    EMBEDDER_PROVIDER: str = Field(default="sentence_transformers")
    VECTOR_STORE_PROVIDER: str = Field(default="chroma")
    RERANKER_PROVIDER: str = Field(default="cross_encoder")
    RETRIEVER_STRATEGY: str = Field(default="hybrid")
    PARSER_STRATEGY: str = Field(default="router")
    CHUNKER_STRATEGY: str = Field(default="structure_aware")
    STORAGE_PROVIDER: str = Field(default="fake")
    # celery (broker/worker) | inline (in-process, no Redis) | fake
    TASK_QUEUE_PROVIDER: str = Field(default="celery")
    TRACER_PROVIDER: str = Field(default="noop")  # noop | otel
    EVAL_HARNESS: str = Field(default="heuristic")  # heuristic | ragas
    # env (os.environ) | gcp_secret_manager (production, lazy SDK)
    SECRET_PROVIDER: str = Field(default="env")

    # Parser fallback chain (priority order), used when PARSER_STRATEGY=router.
    # Lightweight, fully-local parsers first; heavy ones (Docling/Unstructured)
    # as fallbacks. Production may reorder to put docling first.
    PARSER_PRIORITY: str = "plain,pymupdf,docx,tesseract_image,unstructured,docling"

    # --- Provider credentials (unused by fakes; real adapters read these) ---
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    COHERE_API_KEY: str | None = None
    LLAMAPARSE_API_KEY: str | None = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # --- LLM models (per provider) ---
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OLLAMA_MODEL: str = "llama3.1"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024

    # --- RAG generation (Phase 7) ---
    PROMPT_VERSION: str = "v1"
    CHAT_HISTORY_WINDOW: int = 6  # turns kept verbatim before summarizing
    CHAT_SUMMARIZE: bool = True
    NOT_FOUND_MESSAGE: str = (
        "I couldn't find an answer to that in the provided documents."
    )

    # --- Ingestion / storage tuning ---
    LOCAL_STORAGE_DIR: str = "./data/objects"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    # --- Embeddings ---
    # Dim is declared up front so the registry can detect dimension drift
    # (see docs/runbooks/reindex-on-embedder-change.md).
    EMBED_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBED_DIM: int = 384
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBED_DIM: int = 1536

    # --- Chroma ---
    # http (compose/prod) | ephemeral (in-memory) | persistent (local dir)
    CHROMA_MODE: str = "http"
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # --- Observability & evaluation (Phase 9) ---
    OTEL_SERVICE_NAME: str = "rag-platform"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    EVAL_THRESHOLD: float = 0.6  # min per-metric score for a passing scorecard

    # --- Secrets & cloud deployment (Phase 10) ---
    # Optional prefix applied to env-var lookups by the `env` secret provider.
    SECRET_ENV_PREFIX: str = ""
    # GCP project + secret version, read by the gcp_secret_manager provider.
    GCP_PROJECT_ID: str | None = None
    GCP_REGION: str = "us-central1"
    GCP_SECRET_VERSION: str = "latest"

    # --- Retrieval (Phase 5) ---
    RRF_K: int = 60  # Reciprocal Rank Fusion damping constant
    RETRIEVE_TOP_K: int = 5

    # --- Reranking & context assembly (Phase 6) ---
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    COHERE_RERANK_MODEL: str = "rerank-english-v3.0"
    RERANK_FETCH_K: int = 20  # candidates fetched before reranking to top_k
    CONTEXT_TOKEN_BUDGET: int = 2000  # max tokens packed into assembled context
    MMR_LAMBDA: float = 0.7  # relevance vs diversity in the MMR pass
    DEDUP_JACCARD: float = 0.9  # near-duplicate chunk threshold

    # --- Async ingestion (Phase 4) ---
    INGEST_MAX_ATTEMPTS: int = 3
    INGEST_BACKOFF_BASE: float = 0.5  # seconds; doubles each retry
    MAX_BULK_DOCS: int = 200  # max entries accepted from one bulk (zip) upload
    # Simple in-process ingestion rate limit: max enqueues per window.
    INGEST_RATE_LIMIT: int = 100
    INGEST_RATE_WINDOW_SECONDS: float = 60.0
    # Login attempt rate limit (per process).
    LOGIN_RATE_LIMIT: int = 20
    LOGIN_RATE_WINDOW_SECONDS: float = 60.0


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
