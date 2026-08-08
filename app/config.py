"""Central configuration, loaded once from the environment.

Everything the app and its tools need is read here so the rest of the code
never touches ``os.environ`` directly. Keeping it in one dataclass also makes
the app trivial to unit test — just build a ``Config`` by hand.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    # --- OpenAI ---
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str | None

    # --- Database ---
    db_path: str
    db_allow_writes: bool

    # --- Web search ---
    tavily_api_key: str | None

    # --- File system ---
    workspace_dir: str

    # --- Email (SMTP send / IMAP read) ---
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_password: str | None
    email_from: str | None
    email_dry_run: bool
    imap_host: str | None
    imap_port: int
    imap_user: str | None
    imap_password: str | None

    # --- Shell tool ---
    shell_enabled: bool
    shell_timeout: int
    shell_workdir: str | None

    # --- Agent ---
    max_steps: int

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            openai_base_url=os.getenv("OPENAI_BASE_URL"),
            db_path=os.getenv("DB_PATH", "data/ecommerce.db"),
            db_allow_writes=_bool(os.getenv("DB_ALLOW_WRITES"), False),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            workspace_dir=os.getenv("WORKSPACE_DIR", "workspace"),
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            email_from=os.getenv("EMAIL_FROM") or os.getenv("SMTP_USER"),
            email_dry_run=_bool(os.getenv("EMAIL_DRY_RUN"), True),
            imap_host=os.getenv("IMAP_HOST"),
            imap_port=int(os.getenv("IMAP_PORT", "993")),
            # Default IMAP credentials to the SMTP ones (same mailbox).
            imap_user=os.getenv("IMAP_USER") or os.getenv("SMTP_USER"),
            imap_password=os.getenv("IMAP_PASSWORD") or os.getenv("SMTP_PASSWORD"),
            shell_enabled=_bool(os.getenv("SHELL_TOOL_ENABLED"), False),
            shell_timeout=int(os.getenv("SHELL_TIMEOUT", "30")),
            shell_workdir=os.getenv("SHELL_WORKDIR"),
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "12")),
        )

    # Convenience -----------------------------------------------------------
    @property
    def workspace_path(self) -> Path:
        return Path(self.workspace_dir).resolve()
