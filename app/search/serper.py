"""Serper.dev (Google Search) backend."""

from __future__ import annotations

import httpx

from app.models.schemas import SearchHit
from app.search.base import SearchBackend


class SerperBackend(SearchBackend):
    name = "serper"
    _endpoint = "https://google.serper.dev/search"

    def __init__(self, api_key: str, *, timeout: float = 20.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        headers = {"X-API-KEY": self._api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": limit}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(self._endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        hits: list[SearchHit] = []
        for r in data.get("organic", [])[:limit]:
            hits.append(
                SearchHit(
                    title=r.get("title", ""),
                    url=r.get("link", ""),
                    snippet=r.get("snippet", ""),
                    backend=self.name,
                    published=r.get("date"),
                    raw_score=(1.0 / r["position"]) if r.get("position") else None,
                )
            )
        return hits
