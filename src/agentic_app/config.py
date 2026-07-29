"""Centralized configuration loaded from environment / .env.

Shared by both the agent app and the MCP server so a single source of truth
drives model selection, the MCP endpoint, the SQLite path, and tool credentials.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- OpenAI ----
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    # ---- Remote MCP server ----
    mcp_server_url: str = "http://localhost:8000/mcp"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_db_path: str = "./data/clients.db"

    # ---- Web search ----
    tavily_api_key: str | None = None

    # ---- Custom tools ----
    fx_api_base: str = "https://open.er-api.com/v6/latest"

    # ---- Observability (Langfuse) ----
    # Tracing is enabled only when both keys are present; otherwise it's a no-op.
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
