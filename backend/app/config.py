"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

# Load variables from a local .env file if present (no-op in production).
load_dotenv()


class Settings:
    """Runtime settings sourced from the environment.

    Everything has a sensible default so the app can boot without a full
    configuration, but a valid ``OPENAI_API_KEY`` is required to actually
    generate JSON.
    """

    def __init__(self) -> None:
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        # Base URL override lets you point at Azure/OpenAI-compatible gateways.
        self.openai_base_url: str | None = os.getenv("OPENAI_BASE_URL") or None
        self.model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # How many times we ask the model to fix invalid output before giving up.
        self.max_correction_attempts: int = int(
            os.getenv("MAX_CORRECTION_ATTEMPTS", "3")
        )
        # Lower temperature => more deterministic, better for structured output.
        self.temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0"))
        # Comma-separated list of allowed CORS origins for the frontend.
        self.cors_origins: list[str] = [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if origin.strip()
        ]

    @property
    def is_configured(self) -> bool:
        """True when a real OpenAI API key is available.

        The ``sk-...`` placeholder shipped in ``.env.example`` counts as
        unconfigured so the UI and API can give a clear "add your key" message
        instead of a confusing upstream 401.
        """
        key = self.openai_api_key.strip()
        return bool(key) and key != "sk-..."


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()
