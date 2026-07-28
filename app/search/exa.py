"""Exa (neural search) backend with content retrieval."""

from __future__ import annotations

import httpx

from app.models.schemas import SearchHit
from app.search.base import SearchBackend


class ExaBackend(SearchBackend):
    name = "exa"
    _endpoint = "https://api.exa.ai/search"

    def __init__(self, api_key: str, *, timeout: float = 25.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        headers = {"x-api-key": self._api_key, "Content-Type": "application/json"}
        payload = {
            "query": query,
            "numResults": limit,
            "type": "auto",
            "contents": {"text": {"maxCharacters": 2000}},
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(self._endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        hits: list[SearchHit] = []
        for r in data.get("results", []):
            text = r.get("text", "") or ""
            hits.append(
                SearchHit(
                    title=r.get("title", "") or r.get("url", ""),
                    url=r.get("url", ""),
                    snippet=text[:500],
                    backend=self.name,
                    published=r.get("publishedDate"),
                    raw_score=r.get("score"),
                )
            )
        return hits
