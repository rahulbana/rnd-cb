"""Application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    fast_model: str = Field(default="claude-haiku-4-5-20251001", alias="FAST_MODEL")
    smart_model: str = Field(default="claude-sonnet-5", alias="SMART_MODEL")

    # Search backends
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    serper_api_key: str = Field(default="", alias="SERPER_API_KEY")
    exa_api_key: str = Field(default="", alias="EXA_API_KEY")

    # Persistence
    database_url: str = Field(default="", alias="DATABASE_URL")

    # Observability
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", alias="LANGFUSE_HOST")

    # Budget / safety caps
    max_iterations: int = Field(default=5, alias="MAX_ITERATIONS")
    max_usd_cost: float = Field(default=2.50, alias="MAX_USD_COST")
    max_searches_per_iteration: int = Field(default=6, alias="MAX_SEARCHES_PER_ITERATION")
    max_sources: int = Field(default=40, alias="MAX_SOURCES")

    @property
    def has_postgres(self) -> bool:
        return bool(self.database_url)

    @property
    def has_langfuse(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    def enabled_backends(self) -> list[str]:
        backends = ["arxiv"]  # keyless
        if self.tavily_api_key:
            backends.append("tavily")
        if self.serper_api_key:
            backends.append("serper")
        if self.exa_api_key:
            backends.append("exa")
        return backends


@lru_cache
def get_settings() -> Settings:
    return Settings()
