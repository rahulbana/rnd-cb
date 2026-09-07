"""GCP Secret Manager secret provider -- the production backend.

The ``google-cloud-secret-manager`` SDK is imported lazily inside the client
factory so importing this module (in tests, tooling, or the registry) never
requires the SDK or GCP credentials. Resolved secrets are cached in-process;
the ``gcp`` extra installs the SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.config import Settings


class GCPSecretManagerProvider:
    """Resolves secrets from Google Secret Manager (latest version)."""

    name = "gcp_secret_manager"

    def __init__(self, project_id: str, *, version: str = "latest") -> None:
        if not project_id:
            raise ValueError(
                "GCP_PROJECT_ID is required when SECRET_PROVIDER=gcp_secret_manager"
            )
        self._project_id = project_id
        self._version = version
        self._client: Any | None = None
        self._cache: dict[str, str | None] = {}

    @classmethod
    def from_settings(cls, settings: Settings) -> GCPSecretManagerProvider:
        return cls(settings.GCP_PROJECT_ID or "", version=settings.GCP_SECRET_VERSION)

    def _get_client(self) -> Any:
        if self._client is None:
            # Lazy import: only production (with the `gcp` extra installed) pays
            # for the SDK. Keeps the module import-safe everywhere else.
            from google.cloud import secretmanager  # noqa: PLC0415

            self._client = secretmanager.SecretManagerServiceClient()
        return self._client

    def get(self, name: str, *, default: str | None = None) -> str | None:
        if name in self._cache:
            return self._cache[name]
        resource = f"projects/{self._project_id}/secrets/{name}/versions/{self._version}"
        try:
            response = self._get_client().access_secret_version(name=resource)
            value: str | None = response.payload.data.decode("utf-8")
        except Exception:
            # A missing secret (or a permission error) falls back to the default
            # so a partially-provisioned environment degrades predictably.
            value = default
        self._cache[name] = value
        return value
