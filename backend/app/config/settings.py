"""Application configuration.

All settings are sourced from environment variables (or a local ``.env`` file)
so that no secrets are ever committed to the repository. See ``.env.example``.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App -----------------------------------------------------------------
    app_name: str = "TravelPlanner"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # --- Security ------------------------------------------------------------
    # NOTE: override in production. Never rely on the default secret.
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # --- Persistence ---------------------------------------------------------
    # SQLite by default so the app runs with zero external services.
    # In production point this at PostgreSQL, e.g.
    #   postgresql+psycopg://user:pass@host:5432/travelplanner
    database_url: str = "sqlite+pysqlite:///./travelplanner.db"
    redis_url: str | None = None  # optional; used for caching/rate-limit when set

    # --- LLM -----------------------------------------------------------------
    # When no API key is present the app transparently falls back to a
    # deterministic mock provider so the whole system remains runnable offline.
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    llm_model_fast: str = "gpt-4o-mini"
    llm_model_strong: str = "gpt-4o"
    llm_request_timeout_seconds: float = 45.0
    llm_max_retries: int = 2

    # --- External tool APIs (all optional; tools degrade to estimates) -------
    weather_api_key: str | None = None
    maps_api_key: str | None = None

    # --- Observability -------------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = False

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
