"""Registry that owns the available cloud providers."""
from __future__ import annotations

from typing import Optional

from .base import CloudProvider
from .gdrive import GoogleDriveProvider
from .onedrive import OneDriveProvider


class CloudManager:
    """Holds one instance of each provider and looks them up by id."""

    def __init__(self) -> None:
        self._providers: dict[str, CloudProvider] = {}
        for provider in (GoogleDriveProvider(), OneDriveProvider()):
            self._providers[provider.id] = provider

    def providers(self) -> list[CloudProvider]:
        return list(self._providers.values())

    def get(self, provider_id: str) -> Optional[CloudProvider]:
        return self._providers.get(provider_id)
