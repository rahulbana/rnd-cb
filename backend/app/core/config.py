"""Application settings, loaded from environment / .env via pydantic-settings.

Centralising configuration here (instead of scattered ``os.getenv`` calls) gives
us validation, typing, and a single import surface for the whole app.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- LLM ----
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2

    # ---- Web search ----
    # "auto" picks tavily when a key is present, else duckduckgo.
    search_provider: Literal["auto", "tavily", "duckduckgo"] = "auto"
    tavily_api_key: str = ""

    # ---- Agent behaviour ----
    num_subqueries: int = 4
    results_per_query: int = 4

    # ---- Report length / depth ----
    report_max_tokens: int = 4000
    report_target_words: int = 800
    source_content_chars: int = 2000

    # ---- API / server ----
    api_prefix: str = "/api"
    frontend_origin: str = "*"

    # ---- Logging ----
    log_level: str = "INFO"
    log_to_file: bool = False
    log_file: str = "logs/app.log"
    log_max_bytes: int = 10 * 1024 * 1024  # 10 MB per file
    log_backup_count: int = 5  # keep this many rotated files

    # ---- Run history (tracing store) ----
    persist_runs: bool = True
    runs_db_path: str = "data/runs.db"
    runs_list_limit: int = 100

    @property
    def resolved_search_provider(self) -> str:
        """Concrete provider name after resolving the 'auto' setting."""
        if self.search_provider == "auto":
            return "tavily" if self.tavily_api_key else "duckduckgo"
        return self.search_provider


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (safe to use as a FastAPI dependency)."""
    return Settings()
