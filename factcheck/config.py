"""Configuration and shared client construction."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # Pull values from a local .env file if present.

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


class ConfigError(RuntimeError):
    """Raised when required configuration (e.g. API keys) is missing."""


@dataclass
class Settings:
    openai_api_key: str
    tavily_api_key: str
    model: str = DEFAULT_MODEL

    @classmethod
    def from_env(cls, model: str | None = None) -> "Settings":
        openai_key = os.getenv("OPENAI_API_KEY")
        tavily_key = os.getenv("TAVILY_API_KEY")

        missing = [
            name
            for name, value in (("OPENAI_API_KEY", openai_key), ("TAVILY_API_KEY", tavily_key))
            if not value
        ]
        if missing:
            raise ConfigError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ".\nSet them in your shell or copy .env.example to .env and fill them in."
            )

        return cls(
            openai_api_key=openai_key,  # type: ignore[arg-type]
            tavily_api_key=tavily_key,  # type: ignore[arg-type]
            model=model or DEFAULT_MODEL,
        )
