"""Central configuration for cribasagent.

All tunables live here so the rest of the package stays free of magic
values. Values can be overridden via environment variables (see ``.env.example``)
which makes the agent easy to run from cron, a container, or a laptop.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .sources import DEFAULT_SOURCES, NewsSource


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Config:
    """Runtime configuration for a single agent run."""

    # --- LLM (OpenAI) ---
    openai_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )
    model: str = field(
        default_factory=lambda: os.environ.get("CRIBAS_MODEL", "gpt-4o-mini")
    )
    temperature: float = field(
        default_factory=lambda: _env_float("CRIBAS_TEMPERATURE", 0.2)
    )

    # --- News ingestion ---
    sources: list[NewsSource] = field(default_factory=lambda: list(DEFAULT_SOURCES))
    # Only consider articles published within this many hours of "now".
    lookback_hours: int = field(
        default_factory=lambda: _env_int("CRIBAS_LOOKBACK_HOURS", 24)
    )
    # Upper bound on articles fed to the LLM, to keep cost predictable.
    max_articles: int = field(
        default_factory=lambda: _env_int("CRIBAS_MAX_ARTICLES", 120)
    )
    # Articles per LLM map-call (the map step of map-reduce summarisation).
    batch_size: int = field(default_factory=lambda: _env_int("CRIBAS_BATCH_SIZE", 12))
    # Network timeout (seconds) for fetching feeds.
    request_timeout: int = field(
        default_factory=lambda: _env_int("CRIBAS_REQUEST_TIMEOUT", 20)
    )
    # Keep items whose feed provides no parseable date (treated as fresh).
    # Prevents a feed's odd date format from silently zeroing the run.
    keep_undated: bool = field(
        default_factory=lambda: os.environ.get("CRIBAS_KEEP_UNDATED", "1")
        not in ("0", "false", "False", "")
    )
    # Disable TLS verification. Only needed behind a TLS-intercepting proxy that
    # injects a self-signed root. Off by default; drops authenticity checks.
    insecure_ssl: bool = field(
        default_factory=lambda: os.environ.get("CRIBAS_INSECURE_SSL", "0")
        in ("1", "true", "True", "yes")
    )

    # --- Output ---
    output_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("CRIBAS_OUTPUT_DIR", "output")
        ).expanduser()
    )

    # --- Scheduling ---
    run_at: str = field(
        default_factory=lambda: os.environ.get("CRIBAS_RUN_AT", "10:00")
    )

    def validate(self) -> None:
        """Fail fast with a clear message when something essential is missing."""
        if not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export it or add it to a .env file."
            )
        if not self.sources:
            raise RuntimeError("No news sources configured.")
