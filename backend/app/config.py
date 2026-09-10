"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Runtime settings sourced from the environment.

    Kept intentionally light-weight (no pydantic-settings dependency) so the
    surface area is easy to read.
    """

    def __init__(self) -> None:
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_base_url: str | None = os.getenv("OPENAI_BASE_URL") or None
        # Comma-separated list of allowed CORS origins for the React dev server.
        self.cors_origins: list[str] = [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if origin.strip()
        ]

    @property
    def llm_enabled(self) -> bool:
        """Whether a real OpenAI key is configured.

        When False the app falls back to a deterministic local generator so the
        product still works end-to-end without a key.
        """

        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
