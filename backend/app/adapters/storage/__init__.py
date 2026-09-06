"""Object storage adapters."""

from app.adapters.storage.fake_storage import FakeObjectStorage
from app.adapters.storage.local_disk import LocalDiskStorage

__all__ = ["FakeObjectStorage", "LocalDiskStorage"]
