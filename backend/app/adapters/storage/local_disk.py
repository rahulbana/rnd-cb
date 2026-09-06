"""Local-disk object storage adapter.

The dev/default ObjectStorage: raw uploaded files live under a base directory.
GCS and S3 adapters implement the same port later without touching callers.
Keys are namespaced paths (e.g. ``<org_id>/<checksum>``); traversal outside the
base directory is rejected.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings


class LocalDiskStorage:
    """Stores blobs on the local filesystem under a base directory."""

    name = "local_disk"

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir).resolve()

    @classmethod
    def from_settings(cls, settings: Settings) -> LocalDiskStorage:
        return cls(settings.LOCAL_STORAGE_DIR)

    def _path_for(self, key: str) -> Path:
        # Reject absolute keys and path traversal.
        candidate = (self._base / key).resolve()
        if not candidate.is_relative_to(self._base):
            raise ValueError(f"Illegal storage key: {key!r}")
        return candidate

    async def put(self, key: str, data: bytes, *, content_type: str) -> str:
        path = self._path_for(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(_write)
        return path.as_uri()

    async def get(self, key: str) -> bytes:
        path = self._path_for(key)
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, key: str) -> None:
        path = self._path_for(key)

        def _delete() -> None:
            path.unlink(missing_ok=True)

        await asyncio.to_thread(_delete)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._path_for(key).exists)
