"""Typed, validated application settings (pydantic-settings).

Settings are read from environment variables (and an optional `.env` file),
validated once, and cached for the lifetime of the process.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---------------------------------------------------- #
    app_name: str = "Multi-Agent Study Planner"
    app_version: str = "1.0.0"
    log_level: str = Field(default="INFO")

    # --- OpenAI / LLM --------------------------------------------------- #
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    llm_request_timeout: float = Field(default=120.0, ge=1)
    llm_max_retries: int = Field(default=2, ge=0, le=10)

    # --- CORS ----------------------------------------------------------- #
    # Stored raw; exposed as a list via `cors_origins_list` to avoid the
    # JSON-parsing pydantic-settings applies to complex (list) env values.
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173"
    )

    # --- Web research (grounds quiz generation) ------------------------- #
    web_research: bool = Field(default=True)
    tavily_api_key: str = Field(default="")
    research_max_results: int = Field(default=4, ge=1, le=20)
    research_timeout: float = Field(default=14.0, ge=1)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_api_key(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
