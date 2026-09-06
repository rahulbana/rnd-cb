"""ObjectStorage port -- stores and retrieves raw uploaded files."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class ObjectStorage(Protocol):
    """Any blob store (local disk, GCS, S3) must satisfy this."""

    name: str  # "local_disk" | "gcs" | "s3" | ...

    @classmethod
    def from_settings(cls, settings: Settings) -> ObjectStorage:
        """Construct the adapter from application settings."""
        ...

    async def put(self, key: str, data: bytes, *, content_type: str) -> str:
        """Store bytes under ``key`` and return the storage URI."""
        ...

    async def get(self, key: str) -> bytes:
        """Retrieve bytes stored under ``key``."""
        ...

    async def delete(self, key: str) -> None:
        """Remove the object stored under ``key``."""
        ...

    async def exists(self, key: str) -> bool:
        """Whether an object exists under ``key``."""
        ...
