"""Configuration handling: environment loading and default review perspectives."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv

from .models import ReviewCategory

# ---------------------------------------------------------------------------
# Review perspectives
# ---------------------------------------------------------------------------
# These are the "perspectives" the agent inspects. The list is intentionally
# data-driven so it is trivial to extend without touching the review engine.
DEFAULT_CATEGORIES: List[ReviewCategory] = [
    ReviewCategory(
        key="security",
        title="Security",
        guidance=(
            "Look for injection flaws (SQL/command/LDAP), insecure "
            "deserialization, hard-coded secrets or credentials, weak or "
            "missing cryptography, path traversal, SSRF, unsafe use of eval/"
            "exec, missing input validation, insecure defaults, and exposure "
            "of sensitive data."
        ),
    ),
    ReviewCategory(
        key="data_type",
        title="Data Types",
        guidance=(
            "Look for type mismatches, unsafe or implicit conversions, "
            "null/None dereferences, integer overflow, precision loss, "
            "mutable default arguments, incorrect use of collections, and "
            "missing or wrong type annotations."
        ),
    ),
    ReviewCategory(
        key="harmful_code",
        title="Harmful Code",
        guidance=(
            "Look for destructive or malicious behavior: data-wiping commands, "
            "backdoors, unauthorized network exfiltration, fork bombs, "
            "resource exhaustion, obfuscated payloads, or anything that could "
            "damage the host or user data."
        ),
    ),
    ReviewCategory(
        key="performance",
        title="Performance",
        guidance=(
            "Look for inefficient algorithms, needless allocations, N+1 "
            "queries, blocking I/O on hot paths, unbounded memory growth, and "
            "obvious complexity problems."
        ),
    ),
    ReviewCategory(
        key="error_handling",
        title="Error Handling",
        guidance=(
            "Look for swallowed exceptions, bare excepts, unhandled edge "
            "cases, missing resource cleanup, and error paths that leak "
            "sensitive information."
        ),
    ),
    ReviewCategory(
        key="best_practices",
        title="Best Practices & Maintainability",
        guidance=(
            "Look for readability problems, dead code, duplication, poor "
            "naming, missing documentation for complex logic, and violations "
            "of well-established idioms for the language."
        ),
    ),
]


@dataclass
class Settings:
    """Runtime settings for a review run."""

    api_key: str
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 4096
    request_timeout: float = 60.0
    max_retries: int = 4
    concurrency: int = 4
    max_file_bytes: int = 200_000  # skip files larger than this
    categories: Optional[List[ReviewCategory]] = None

    def resolved_categories(self) -> List[ReviewCategory]:
        return self.categories or DEFAULT_CATEGORIES


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


def load_settings(
    env_file: Optional[str] = None,
    *,
    model: Optional[str] = None,
    concurrency: Optional[int] = None,
) -> Settings:
    """Build :class:`Settings` from a ``.env`` file and the environment.

    Environment variables (``.env`` or process env) that are honoured:

    * ``OPENAI_API_KEY``   (required)
    * ``OPENAI_MODEL``     (default ``gpt-4o-mini``)
    * ``OPENAI_BASE_URL``  (optional, for Azure/OpenAI-compatible gateways)
    * ``REVIEW_TEMPERATURE``, ``REVIEW_MAX_TOKENS``, ``REVIEW_TIMEOUT``,
      ``REVIEW_MAX_RETRIES``, ``REVIEW_CONCURRENCY``, ``REVIEW_MAX_FILE_BYTES``
    """

    # ``load_dotenv`` will look for a .env in the CWD / parents when no path is
    # given. Existing process env vars take precedence (override=False).
    if env_file:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "OPENAI_API_KEY is not set. Create a .env file (see .env.example) "
            "or export the variable before running."
        )

    def _float(name: str, default: float) -> float:
        raw = os.getenv(name)
        try:
            return float(raw) if raw is not None else default
        except ValueError:
            return default

    def _int(name: str, default: int) -> int:
        raw = os.getenv(name)
        try:
            return int(raw) if raw is not None else default
        except ValueError:
            return default

    return Settings(
        api_key=api_key,
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        temperature=_float("REVIEW_TEMPERATURE", 0.0),
        max_tokens=_int("REVIEW_MAX_TOKENS", 4096),
        request_timeout=_float("REVIEW_TIMEOUT", 60.0),
        max_retries=_int("REVIEW_MAX_RETRIES", 4),
        concurrency=concurrency or _int("REVIEW_CONCURRENCY", 4),
        max_file_bytes=_int("REVIEW_MAX_FILE_BYTES", 200_000),
    )
