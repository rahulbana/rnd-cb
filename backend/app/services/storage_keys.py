"""Deterministic object-storage keys.

The upload path and the async job runner both derive the same content-addressed
key from a document's fields, so the worker can fetch the raw bytes the API
stored without persisting the key separately.
"""

from __future__ import annotations

from pathlib import Path


def object_key(org_id: str, checksum: str, filename: str) -> str:
    """Content-addressed key: ``<org_id>/<checksum><ext>``."""
    suffix = Path(filename).suffix
    return f"{org_id}/{checksum}{suffix}"
