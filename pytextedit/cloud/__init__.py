"""Cloud storage integration.

Each provider (Google Drive, OneDrive, ...) implements :class:`CloudProvider`
so the UI can treat them interchangeably.
"""
from .base import CloudProvider, CloudFile, CloudError

__all__ = ["CloudProvider", "CloudFile", "CloudError"]
