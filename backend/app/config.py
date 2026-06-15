"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Runtime settings sourced from the environment."""

    def __init__(self) -> None:
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        raw_origins = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
        self.cors_origins: list[str] = [
            origin.strip() for origin in raw_origins.split(",") if origin.strip()
        ]

        # Web research used to ground quiz generation in board materials.
        self.web_research: bool = os.getenv("WEB_RESEARCH", "true").lower() not in (
            "0",
            "false",
            "no",
            "off",
        )
        self.tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
        try:
            self.research_max_results: int = int(os.getenv("RESEARCH_MAX_RESULTS", "4"))
        except ValueError:
            self.research_max_results = 4

    @property
    def has_api_key(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
