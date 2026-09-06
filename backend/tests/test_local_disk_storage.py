"""LocalDiskStorage adapter round-trip and safety."""

from __future__ import annotations

import pytest

from app.adapters.storage import LocalDiskStorage


@pytest.mark.asyncio
async def test_put_get_exists_delete(tmp_path):
    store = LocalDiskStorage(str(tmp_path / "objects"))
    key = "org1/abc123.pdf"

    assert await store.exists(key) is False
    uri = await store.put(key, b"payload", content_type="application/pdf")
    assert uri.startswith("file://")
    assert await store.exists(key) is True
    assert await store.get(key) == b"payload"

    await store.delete(key)
    assert await store.exists(key) is False


@pytest.mark.asyncio
async def test_rejects_path_traversal(tmp_path):
    store = LocalDiskStorage(str(tmp_path / "objects"))
    with pytest.raises(ValueError):
        await store.put("../escape.txt", b"x", content_type="text/plain")
