"""Runtime configuration.

Values are read from environment variables so the same code runs in local dev,
CI, and a container without edits. Nothing here requires an LLM API key: the
default planner is fully offline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    datasets_dir: Path = ROOT / "datasets"
    reports_dir: Path = ROOT / "reports"

    # Planner backend: "heuristic" (offline, default) or "llm".
    planner_backend: str = os.getenv("PLANNER_BACKEND", "heuristic")
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-5")

    # Safety cap so an accidental "1 billion rows" prompt cannot OOM the host.
    max_rows: int = int(os.getenv("MAX_ROWS", "2000000"))

    def ensure_dirs(self) -> None:
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
