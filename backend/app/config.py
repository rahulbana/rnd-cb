"""Application configuration loaded from environment variables / .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the chatbot backend.

    Values are read from environment variables (case-insensitive) or a local
    ``.env`` file. See ``.env.example`` for documentation of each field.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- OpenAI / LLM --------------------------------------------------------
    openai_api_key: str = ""
    # Optional custom base URL (e.g. Azure OpenAI or an OpenAI-compatible
    # gateway). Leave empty to use the default OpenAI endpoint.
    openai_base_url: str = ""
    # Default model. See app/llm.py for temperature-support gating: OpenAI
    # reasoning models (o1, o3, gpt-5, ...) reject a custom `temperature`, so
    # the per-conversation temperature only applies to standard chat models
    # (e.g. gpt-4o, gpt-4o-mini, gpt-4-turbo).
    model: str = "gpt-4o-mini"
    max_tokens: int = 4096

    # --- Conversation defaults ----------------------------------------------
    default_system_prompt: str = "You are a helpful, concise assistant."
    default_temperature: float = 1.0

    # --- Authentication (HTTP Basic) ----------------------------------------
    auth_username: str = "admin"
    auth_password: str = "changeme"

    # --- Database ------------------------------------------------------------
    database_url: str = "sqlite+aiosqlite:///./chatbot.db"

    # --- Server / CORS -------------------------------------------------------
    # Comma-separated list of allowed origins for the frontend dev server.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Logging -------------------------------------------------------------
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
