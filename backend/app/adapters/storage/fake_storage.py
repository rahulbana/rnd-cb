"""In-memory fake object storage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings


class FakeObjectStorage:
    """Process-local blob store keyed by object key."""

    name = "fake"

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    @classmethod
    def from_settings(cls, settings: Settings) -> FakeObjectStorage:
        return cls()

    async def put(self, key: str, data: bytes, *, content_type: str) -> str:
        self._blobs[key] = data
        return f"fake://{key}"

    async def get(self, key: str) -> bytes:
        return self._blobs[key]

    async def delete(self, key: str) -> None:
        self._blobs.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._blobs
