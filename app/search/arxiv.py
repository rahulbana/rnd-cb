"""arXiv backend — keyless academic search via the arXiv Atom API.

Stands in for the "arxiv MCP" backend named in the spec: same role (peer-reviewed
/ preprint academic sources), exposed through the uniform SearchBackend interface.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from app.models.schemas import SearchHit
from app.search.base import SearchBackend

_ATOM = "{http://www.w3.org/2005/Atom}"


class ArxivBackend(SearchBackend):
    name = "arxiv"
    _endpoint = "http://export.arxiv.org/api/query"

    def __init__(self, *, timeout: float = 20.0) -> None:
        self._timeout = timeout

    async def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(self._endpoint, params=params)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)

        hits: list[SearchHit] = []
        for entry in root.findall(f"{_ATOM}entry"):
            title = (entry.findtext(f"{_ATOM}title") or "").strip()
            summary = (entry.findtext(f"{_ATOM}summary") or "").strip()
            published = entry.findtext(f"{_ATOM}published")
            url = ""
            for link in entry.findall(f"{_ATOM}link"):
                if link.get("type") == "text/html" or link.get("rel") == "alternate":
                    url = link.get("href", "")
                    break
            hits.append(
                SearchHit(
                    title=title,
                    url=url,
                    snippet=summary[:500],
                    backend=self.name,
                    published=published,
                )
            )
        return hits
