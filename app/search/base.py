"""Search backend interface.

Every backend implements a single async `search` method returning `SearchHit`s.
Backends must be resilient: a network/auth failure returns `[]` (logged) rather
than raising, so one dead backend never kills a research run.
"""

from __future__ import annotations

import abc
import logging

from app.models.schemas import SearchHit

logger = logging.getLogger(__name__)


class SearchBackend(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        """Return up to `limit` hits for `query`. Never raises on backend errors."""

    async def safe_search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        try:
            return await self.search(query, limit=limit)
        except Exception as exc:  # noqa: BLE001 — deliberate: isolate backend failures
            logger.warning("backend %s failed for query %r: %s", self.name, query, exc)
            return []
