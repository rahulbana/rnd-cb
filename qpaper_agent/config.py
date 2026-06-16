"""Runtime configuration for the question-paper agent system.

All settings can be overridden through environment variables (loaded from a
local ``.env`` file when present) so that nothing sensitive is hard-coded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:  # python-dotenv is optional at runtime but recommended.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a convenience only.
    pass


@dataclass(frozen=True)
class Settings:
    """Immutable view of the system configuration."""

    openai_api_key: str
    # Model used for planning / validation (reasoning over text).
    model: str
    # Model used by the search agent. It must support the web_search tool.
    search_model: str
    # Where downloaded papers are written.
    output_dir: str
    # Per-request HTTP timeout (seconds) used by the downloader.
    request_timeout: int
    # Upper bound on candidates carried between stages, to keep runs cheap.
    max_candidates: int

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        return cls(
            openai_api_key=api_key,
            model=os.getenv("QPAPER_MODEL", "gpt-4o"),
            search_model=os.getenv("QPAPER_SEARCH_MODEL", "gpt-4o"),
            output_dir=os.getenv("QPAPER_OUTPUT_DIR", "downloads"),
            request_timeout=int(os.getenv("QPAPER_HTTP_TIMEOUT", "60")),
            max_candidates=int(os.getenv("QPAPER_MAX_CANDIDATES", "25")),
        )

    def require_api_key(self) -> None:
        """Raise a helpful error if the OpenAI API key is missing."""
        if not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export it or add it to a .env file. "
                "See .env.example for the expected variables."
            )
