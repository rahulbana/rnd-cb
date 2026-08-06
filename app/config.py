"""Central configuration, loaded from environment / .env file."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (parent of the `app` package).
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application configuration resolved from the environment."""

    # LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    # Optional keys
    CALENDARIFIC_API_KEY: str = os.getenv("CALENDARIFIC_API_KEY", "").strip()
    NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY", "").strip()

    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1").strip()
    PORT: int = int(os.getenv("PORT", "8765"))

    # Paths
    EXPORT_DIR: Path = BASE_DIR / os.getenv("EXPORT_DIR", "exports")
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = DATA_DIR / "agent.db"
    FRONTEND_DIR: Path = BASE_DIR / "app" / "frontend"
    LOG_DIR: Path = BASE_DIR / os.getenv("LOG_DIR", "logs")
    UPLOAD_DIR: Path = BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_RETENTION_DAYS: int = int(os.getenv("LOG_RETENTION_DAYS", "30"))

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def has_openai(cls) -> bool:
        return bool(cls.OPENAI_API_KEY)

    @property
    def base_url(self) -> str:
        return f"http://{self.HOST}:{self.PORT}"


config = Config()
config.ensure_dirs()
