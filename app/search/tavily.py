"""Tavily search backend (HTTP; no SDK dependency required at runtime)."""

from __future__ import annotations

import httpx

from app.models.schemas import SearchHit
from app.search.base import SearchBackend


class TavilyBackend(SearchBackend):
    name = "tavily"
    _endpoint = "https://api.tavily.com/search"

    def __init__(self, api_key: str, *, timeout: float = 20.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": limit,
            "search_depth": "advanced",
            "include_answer": False,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(self._endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()

        hits: list[SearchHit] = []
        for r in data.get("results", []):
            hits.append(
                SearchHit(
                    title=r.get("title", "") or r.get("url", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", ""),
                    backend=self.name,
                    published=r.get("published_date"),
                    raw_score=r.get("score"),
                )
            )
        return hits
