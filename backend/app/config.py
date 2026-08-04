"""Runtime configuration and mutable app settings."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load .env from the backend dir or the repo root, whichever exists.
load_dotenv()

PermissionMode = str  # "ask" | "auto"


@dataclass
class Settings:
    """Mutable settings adjustable at runtime from the UI."""

    project_path: str
    model: str
    permission_mode: PermissionMode

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.getenv("AGENT_PERMISSION_MODE", "ask")
        return cls(
            project_path=os.getenv("PROJECT_DIR") or os.getcwd(),
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            permission_mode="auto" if mode == "auto" else "ask",
        )


# Singleton instance shared across the app.
settings = Settings.from_env()


def openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


def has_api_key() -> bool:
    return bool(openai_api_key())


def database_url() -> str | None:
    return os.getenv("DATABASE_URL")


def venv_python() -> str:
    """Python interpreter used to create per-project virtualenvs."""
    return os.getenv("VENV_PYTHON", "python3.12")
