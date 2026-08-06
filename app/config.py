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

    # LLM provider: "openai" or "ollama"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").strip().lower()

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "").strip()

    # Ollama (OpenAI-compatible local server)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip()
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1").strip()

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

    def __init__(self) -> None:
        # Runtime-adjustable LLM state (initialized from the environment).
        provider = self.LLM_PROVIDER if self.LLM_PROVIDER in ("openai", "ollama") else "openai"
        self._provider = provider
        self._models = {"openai": self.OPENAI_MODEL, "ollama": self.OLLAMA_MODEL}

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # ---- LLM provider selection (mutable at runtime) ----

    def active_provider(self) -> str:
        return self._provider

    def active_model(self) -> str:
        return self._models.get(self._provider, "")

    def set_llm(self, provider: str | None = None, model: str | None = None) -> None:
        if provider in ("openai", "ollama"):
            self._provider = provider
        if model:
            self._models[self._provider] = model.strip()

    def llm_configured(self) -> bool:
        """Whether the active provider is usable (Ollama needs no key)."""
        if self._provider == "ollama":
            return True
        return bool(self.OPENAI_API_KEY)

    def llm_base_url(self) -> str | None:
        if self._provider == "ollama":
            return self.OLLAMA_BASE_URL
        return self.OPENAI_BASE_URL or None

    def llm_api_key(self) -> str:
        # Ollama's OpenAI-compatible endpoint ignores the key but the SDK needs one.
        return "ollama" if self._provider == "ollama" else self.OPENAI_API_KEY

    @classmethod
    def has_openai(cls) -> bool:
        return bool(cls.OPENAI_API_KEY)

    @property
    def base_url(self) -> str:
        return f"http://{self.HOST}:{self.PORT}"


config = Config()
config.ensure_dirs()
