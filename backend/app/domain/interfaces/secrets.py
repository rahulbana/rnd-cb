"""SecretProvider port -- resolves named secrets from a backing store.

Local/dev reads from the process environment; production reads from GCP Secret
Manager. Callers depend on this port, never on a cloud SDK, so promoting from
env vars to a managed secret store is a one-line ``.env`` change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class SecretProvider(Protocol):
    """Any secret backend (env, GCP Secret Manager, Vault) must satisfy this."""

    name: str  # "env" | "gcp_secret_manager" | ...

    @classmethod
    def from_settings(cls, settings: Settings) -> SecretProvider:
        """Construct the adapter from application settings."""
        ...

    def get(self, name: str, *, default: str | None = None) -> str | None:
        """Return the secret value for ``name`` or ``default`` if absent."""
        ...
