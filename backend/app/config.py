"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    Values are read from environment variables and an optional .env file
    living next to the backend package.
    """

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # Base URL is configurable so the app can point at Azure/OpenAI-compatible
    # gateways without code changes.
    openai_base_url: str | None = None
    # Comma-separated list of allowed CORS origins for the React dev server.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
