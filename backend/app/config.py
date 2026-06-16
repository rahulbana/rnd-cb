"""Application configuration loaded from environment / .env file."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Values come from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Web search
    search_provider: str = "tavily"
    tavily_api_key: str | None = None
    serpapi_api_key: str | None = None
    search_max_results: int = 8

    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        """True when a real OpenAI key is configured."""
        return bool(self.openai_api_key)

    def resolved_search_provider(self) -> str:
        """Return the usable provider, falling back to 'mock' when keys are absent."""
        provider = (self.search_provider or "mock").lower()
        if provider == "tavily" and not self.tavily_api_key:
            return "mock"
        if provider == "serpapi" and not self.serpapi_api_key:
            return "mock"
        if provider not in {"tavily", "serpapi", "mock"}:
            return "mock"
        return provider


@lru_cache
def get_settings() -> Settings:
    return Settings()
