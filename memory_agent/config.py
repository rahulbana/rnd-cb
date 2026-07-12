"""Configuration for the memory chatbot agent.

Values are read from environment variables (optionally loaded from a local
``.env`` file). Only ``OPENAI_API_KEY`` is strictly required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the agent."""

    # --- OpenAI ---
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    # Allows pointing at Azure/OpenAI-compatible gateways when set.
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL") or None
    chat_model: str = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    temperature: float = float(os.getenv("CHAT_TEMPERATURE", "0.3"))

    # --- Tools ---
    # Optional. Web search is disabled with a friendly message if unset.
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")

    # --- Storage ---
    # Single SQLite file holds the chat log, long-term memories, and the
    # LangGraph short-term checkpoints.
    db_path: str = os.getenv("MEMORY_DB_PATH", "chat_memory.db")

    # --- Observability (Langfuse) ---
    # Optional. Tracing is enabled only when both keys are present; otherwise
    # the app runs exactly as before with no callbacks attached.
    langfuse_public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    langfuse_secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # --- Memory tuning ---
    # How many recent messages of the running conversation are fed to the LLM
    # (the "short-term memory" window). Older turns stay in the checkpoint but
    # are not sent to the model on every call.
    short_term_window: int = int(os.getenv("SHORT_TERM_WINDOW", "20"))
    # How many long-term memories to recall and inject per turn.
    memory_top_k: int = int(os.getenv("MEMORY_TOP_K", "5"))
    # Minimum cosine similarity for a long-term memory to count as relevant.
    memory_min_score: float = float(os.getenv("MEMORY_MIN_SCORE", "0.25"))

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    def require_api_key(self) -> None:
        if not self.openai_api_key:
            raise SystemExit(
                "OPENAI_API_KEY is not set.\n"
                "Set it in your environment or in a .env file, e.g.\n"
                "    export OPENAI_API_KEY=sk-...\n"
                "See .env.example for all supported settings."
            )


settings = Settings()
