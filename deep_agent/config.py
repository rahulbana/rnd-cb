"""Centralised, environment-driven configuration.

All runtime tunables live here so that agents, providers and tasks stay
free of hard-coded values.  Settings are loaded from environment variables
and an optional ``.env`` file via ``pydantic-settings``.
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported (switchable) LLM back-ends."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class SearchProvider(str, Enum):
    """Supported (switchable) web-search back-ends."""

    TAVILY = "tavily"
    SERPER = "serper"


class CheckpointBackend(str, Enum):
    """LangGraph checkpoint persistence backends."""

    NONE = "none"        # no checkpointing
    MEMORY = "memory"    # in-process, lost on exit
    SQLITE = "sqlite"    # persisted to disk, resumable across runs


class CacheBackend(str, Enum):
    """LLM response cache backends."""

    NONE = "none"        # no caching
    MEMORY = "memory"    # in-process, dedupes within a run
    SQLITE = "sqlite"    # persisted to disk, dedupes across runs


class LLMTier(str, Enum):
    """Model tier an agent requests from the factory."""

    FAST = "fast"        # lightweight / cheaper model
    SMART = "smart"      # highest-quality model


class Settings(BaseSettings):
    """Application settings, sourced from env / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- LLM ------------------------------------------------------------
    llm_provider: LLMProvider = Field(default=LLMProvider.OPENAI)
    llm_model: str = Field(default="gpt-4o")
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # --- LLM fine-grained control ---------------------------------------
    # Optional cheaper model for FAST-tier agents (falls back to llm_model).
    llm_fast_model: str | None = None
    # Per-agent model overrides, e.g. LLM_AGENT_MODELS='{"writer":"gpt-4o"}'.
    llm_agent_models: dict[str, str] = Field(default_factory=dict)
    llm_max_tokens: int | None = None
    llm_timeout: int = Field(default=60, ge=1)
    llm_max_retries: int = Field(default=2, ge=0)
    llm_seed: int | None = None

    # --- LLM response cache ---------------------------------------------
    # backend: none | memory | sqlite  (sqlite dedupes across runs)
    llm_cache_backend: CacheBackend = Field(default=CacheBackend.SQLITE)
    llm_cache_path: str = Field(default="deep_agent_llm_cache.sqlite")

    # --- Context budgeting (input-token control) ------------------------
    max_context_chars: int = Field(default=24_000, ge=1_000)
    per_source_chars: int = Field(default=1_500, ge=200)

    # --- Search ---------------------------------------------------------
    search_provider: SearchProvider = Field(default=SearchProvider.TAVILY)
    search_max_results: int = Field(default=6, ge=1, le=25)
    tavily_api_key: str | None = None
    serper_api_key: str | None = None

    # --- Research loop --------------------------------------------------
    max_research_iterations: int = Field(default=3, ge=1, le=10)
    scrape_timeout_seconds: int = Field(default=20, ge=1)
    scrape_max_concurrency: int = Field(default=5, ge=1, le=50)

    # --- Scraper politeness ---------------------------------------------
    scrape_user_agent: str = Field(
        default="DeepAgent/0.1 (+https://example.com/bot)"
    )
    respect_robots: bool = Field(default=True)
    scrape_delay_seconds: float = Field(default=1.0, ge=0.0)

    # --- CLI ------------------------------------------------------------
    stream_progress: bool = Field(default=True)

    # --- Celery ---------------------------------------------------------
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")
    celery_task_always_eager: bool = Field(default=True)

    # --- Checkpointing --------------------------------------------------
    checkpoint_backend: CheckpointBackend = Field(default=CheckpointBackend.MEMORY)
    checkpoint_db: str = Field(default="deep_agent_checkpoints.sqlite")

    # --- Observability (Langfuse) ---------------------------------------
    langfuse_enabled: bool = Field(default=False)
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = Field(default="https://cloud.langfuse.com")

    # --- Logging --------------------------------------------------------
    log_level: str = Field(default="INFO")
    log_dir: str = Field(default="logs")

    # --- Output ---------------------------------------------------------
    output_dir: str = Field(default="docs")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached :class:`Settings` instance."""

    return Settings()
