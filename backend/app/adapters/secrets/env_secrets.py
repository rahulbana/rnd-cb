"""Environment-variable secret provider -- the dev/default backend.

Reads secrets from ``os.environ`` (optionally under a prefix). No cloud SDK,
no network: the same code path a production GCP Secret Manager deployment
swaps out by flipping ``SECRET_PROVIDER``.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings


class EnvSecretProvider:
    """Resolves secrets from the process environment."""

    name = "env"

    def __init__(self, prefix: str = "") -> None:
        self._prefix = prefix

    @classmethod
    def from_settings(cls, settings: Settings) -> EnvSecretProvider:
        return cls(prefix=settings.SECRET_ENV_PREFIX)

    def get(self, name: str, *, default: str | None = None) -> str | None:
        return os.environ.get(f"{self._prefix}{name}", default)
