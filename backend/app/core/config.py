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
    DEFAULT_ORG_ID: str = "00000000-0000-0000-0000-000000000000"

    # --- Datastores ---
    DATABASE_URL: str = "postgresql+psycopg://rag:rag@localhost:5432/rag"
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # --- Provider selection: the swappable core ---
    LLM_PROVIDER: str = Field(default="fake")
    EMBEDDER_PROVIDER: str = Field(default="fake")
    VECTOR_STORE_PROVIDER: str = Field(default="fake")
    RERANKER_PROVIDER: str = Field(default="fake")
    RETRIEVER_STRATEGY: str = Field(default="fake")
    PARSER_STRATEGY: str = Field(default="fake")
    CHUNKER_STRATEGY: str = Field(default="fake")
    STORAGE_PROVIDER: str = Field(default="fake")
    TASK_QUEUE_PROVIDER: str = Field(default="fake")

    # --- Provider credentials (unused by fakes; real adapters read these) ---
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    COHERE_API_KEY: str | None = None
    LLAMAPARSE_API_KEY: str | None = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # --- Ingestion / storage tuning ---
    LOCAL_STORAGE_DIR: str = "./data/objects"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
