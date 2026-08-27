"""Application configuration.

All settings are environment-driven (12-factor). Secrets never live in source.
Load order: process env -> .env file (for local dev only).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "deep-research-agent"
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    # --- OpenAI ---
    openai_api_key: str = Field(default="")
    # Cheaper model for planning/extraction/reflection (many calls).
    openai_model: str = Field(default="gpt-4o-mini")
    # Higher-quality model for the final synthesis (single call).
    openai_synthesis_model: str = Field(default="gpt-4o")
    openai_temperature: float = Field(default=0.0)
    # Guard against a runaway agent hammering the API.
    openai_max_retries: int = Field(default=3)
    llm_request_timeout: float = Field(default=90.0)

    # --- Search ---
    tavily_api_key: str = Field(default="")
    max_results_per_query: int = Field(default=5)
    search_timeout: float = Field(default=25.0)

    # --- Research loop budget (bounds a long-running task) ---
    max_iterations: int = Field(default=4)
    max_queries_per_iteration: int = Field(default=4)

    # --- Persistence ---
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/research"
    )
    db_pool_min_size: int = Field(default=2)
    db_pool_max_size: int = Field(default=10)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        # Allow a comma-separated env string, e.g. CORS_ORIGINS=a,b,c
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def has_tavily(self) -> bool:
        return bool(self.tavily_api_key)


@lru_cache
def get_settings() -> Settings:
    """Cached singleton. Import and call this, do not instantiate Settings directly."""
    return Settings()
