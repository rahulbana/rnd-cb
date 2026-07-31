"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    APP_NAME: str = "AI Content Writer"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- CORS ---
    # Comma separated list of allowed origins for the frontend.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Database ---
    # Defaults to a local SQLite file so the app runs with zero setup.
    # In production set e.g.
    #   postgresql+asyncpg://user:pass@postgres:5432/contentwriter
    DATABASE_URL: str = "sqlite+aiosqlite:///./contentwriter.db"

    # --- Auth / JWT ---
    SECRET_KEY: str = "CHANGE_ME_super_secret_key_for_dev_only"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- OpenAI / LLM ---
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None  # optional (Azure / proxy / local)
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.7
    # gpt-4o / gpt-4o-mini support up to 16k output tokens; keep headroom
    # for long, in-depth articles.
    LLM_MAX_TOKENS: int = 12000

    # --- Embeddings ---
    # Provider: "hash" (default, zero-dependency), "sentence_transformers"
    # or "openai".
    EMBEDDING_PROVIDER: str = "hash"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 384  # used by the hash fallback embedder

    # --- Images (banners) ---
    IMAGE_MODEL: str = "gpt-image-1"
    IMAGE_SIZE: str = "1536x1024"  # landscape banner
    MEDIA_DIR: str = "./media"
    MEDIA_URL_PREFIX: str = "/media"

    # --- Web research ---
    # Provider: "openai" (built-in web search, no extra key), "tavily"
    # (needs TAVILY_API_KEY) or "none" to disable.
    WEB_SEARCH_PROVIDER: str = "openai"
    WEB_SEARCH_MODEL: str = "gpt-4o-mini"  # must support the web_search tool
    TAVILY_API_KEY: str | None = None
    # "Deep" research plans and runs this many focused sub-queries.
    DEEP_RESEARCH_MAX_QUERIES: int = 4
    WEB_SEARCH_MAX_RESULTS: int = 5  # results per query (tavily)

    # --- Observability (Langfuse) ---
    # Tracing activates automatically when both keys are set.
    LANGFUSE_ENABLED: bool = True
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    # Trace every API request as a single trace (full request in / response
    # out, with LLM + tool spans nested). Turn off to trace only LLM calls.
    LANGFUSE_TRACE_REQUESTS: bool = True

    # --- Vector store (ChromaDB) ---
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_COLLECTION: str = "articles"
    # Cosine distance below which two articles are flagged as duplicates.
    DUPLICATE_DISTANCE_THRESHOLD: float = 0.15

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
