"""Runtime configuration for the Ye'ai Assistant.

All settings are read from environment variables (optionally loaded from a
local ``.env`` file) so that no secrets ever live in the source tree.
"""

from __future__ import annotations

import os

try:  # python-dotenv is optional at runtime; the app still works without it.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a convenience only.
    pass


# --- OpenAI -----------------------------------------------------------------
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL") or None

# --- HTTP -------------------------------------------------------------------
def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


HTTP_TIMEOUT: int = _int_env("YEAI_HTTP_TIMEOUT", 20)

# A friendly User-Agent keeps the free public APIs / search endpoints happy.
USER_AGENT: str = (
    "Yeai-Assistant/0.1 (+https://github.com/rahulbana/rnd-cb) "
    "python-requests"
)

# Cap on the number of tool-calling rounds before we force a final answer.
MAX_AGENT_STEPS: int = _int_env("YEAI_MAX_STEPS", 8)
