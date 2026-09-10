"""In-memory translation history with a bounded size.

History is intentionally ephemeral (process-local). It is thread-safe so it
can be used from FastAPI's threadpool-backed sync endpoints.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from datetime import datetime, timezone

from .schemas import HistoryEntry


class HistoryStore:
    def __init__(self, limit: int) -> None:
        self._entries: deque[HistoryEntry] = deque(maxlen=limit)
        self._lock = threading.Lock()

    def add(
        self,
        *,
        original: str,
        translated_text: str,
        source_lang: str,
        detected_source_lang: str,
        target_lang: str,
        style: str,
    ) -> HistoryEntry:
        entry = HistoryEntry(
            id=uuid.uuid4().hex,
            created_at=datetime.now(timezone.utc),
            source_lang=source_lang,
            detected_source_lang=detected_source_lang,
            target_lang=target_lang,
            style=style,
            original=original,
            translated_text=translated_text,
        )
        with self._lock:
            self._entries.appendleft(entry)
        return entry

    def list(self) -> list[HistoryEntry]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
