"""Runtime configuration.

Values are read from environment variables so the same code runs in local dev,
CI, and a container without edits. A local ``.env`` file (git-ignored) is loaded
automatically at import time — copy ``.env.example`` to ``.env`` to configure the
LLM planner. Nothing here requires an LLM API key: the default planner is fully
offline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Load variables from a local .env file if present. Real environment variables
# always take precedence (override=False), so container/CI config is not
# clobbered by a stray .env.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


@dataclass
class Settings:
    datasets_dir: Path = ROOT / "datasets"
    reports_dir: Path = ROOT / "reports"

    # Planner backend: "heuristic" (offline, default) or "llm".
    planner_backend: str = os.getenv("PLANNER_BACKEND", "heuristic")
    # LLM provider for the optional planner: "openai" (default), "anthropic",
    # or "litellm" (multi-provider). Configure the matching API key env var.
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Safety cap so an accidental "1 billion rows" prompt cannot OOM the host.
    max_rows: int = int(os.getenv("MAX_ROWS", "2000000"))

    def ensure_dirs(self) -> None:
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
