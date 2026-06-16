"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env`` file)
using :mod:`pydantic_settings`. Centralising configuration here keeps secrets
and tunables out of the application code and makes the app easy to deploy in
different environments.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application settings.

    Attributes:
        openai_api_key: Secret key used to authenticate against the OpenAI API.
        openai_model: Chat completion model used by all agents.
        openai_temperature: Sampling temperature for the model.
        cors_origins: Origins permitted to call the API from a browser.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.2, alias="OPENAI_TEMPERATURE")
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow ``CORS_ORIGINS`` to be supplied as a comma separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Caching avoids re-reading the environment on every request while still
    allowing tests to clear the cache when they need to override values.
    """
    return Settings()
