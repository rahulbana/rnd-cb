"""Central configuration, loaded from environment / .env file.

All settings are prefixed with ``AUTODEV_`` so they don't collide with
other tools' environment variables.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTODEV_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider selection ---
    llm_provider: str = "openai"  # "openai" | "ollama"

    # --- OpenAI ---
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # --- Generation controls ---
    temperature: float = 0.2
    max_fix_iterations: int = 4
    request_timeout: int = 600

    # --- Sandbox ---
    workspace_root: str = "./workspaces"
    command_timeout: int = 300
    auto_venv: bool = True

    # --- Persistence ---
    database_url: str = "sqlite:///./autodev.db"

    # --- Optional memory ---
    memory_enabled: bool = False
    memory_dir: str = "./memory_store"
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- Server ---
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def workspace_root_path(self) -> Path:
        p = Path(self.workspace_root).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def memory_dir_path(self) -> Path:
        p = Path(self.memory_dir).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
