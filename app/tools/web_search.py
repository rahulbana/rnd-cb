"""Web search + deep web search.

`web_search` returns a list of result snippets (DuckDuckGo, free, no key).
`deep_web_search` additionally fetches the top pages, extracts their text and
(if an LLM is configured) synthesizes a cited answer.
"""
from __future__ import annotations

from .base import Tool, err, http_get, ok

try:
    from ddgs import DDGS
except Exception:  # pragma: no cover
    try:
        from duckduckgo_search import DDGS  # older package name
    except Exception:
        DDGS = None


def _search(query: str, max_results: int) -> list[dict]:
    if DDGS is None:
        raise RuntimeError("Search backend (ddgs) is not installed.")
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title"),
                "url": r.get("href") or r.get("url"),
                "snippet": r.get("body"),
            })
    return results


def web_search(query: str, max_results: int = 6) -> dict:
    """Search the web and return a list of results (title, url, snippet)."""
    try:
        results = _search(query, max_results)
    except Exception as exc:
        return err(f"Web search failed: {exc}")
    return ok({"query": query, "count": len(results), "results": results})


def _extract_text(url: str, max_chars: int = 3000) -> str:
    from bs4 import BeautifulSoup

    resp = http_get(url, timeout=15)
    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    return text[:max_chars]


def deep_web_search(query: str, max_results: int = 5) -> dict:
    """Search the web, read the top pages, and synthesize a cited summary."""
    try:
        results = _search(query, max_results)
    except Exception as exc:
        return err(f"Web search failed: {exc}")
    if not results:
        return ok({"query": query, "results": [], "summary": "No results found."})

    sources = []
    for r in results:
        url = r.get("url")
        if not url:
            continue
        try:
            content = _extract_text(url)
        except Exception:
            content = r.get("snippet") or ""
        sources.append({"title": r.get("title"), "url": url, "content": content})

    summary = None
    # Synthesize with the LLM when available; otherwise return raw extracts.
    from ..agent.client import LLMUnavailable, complete
    try:
        context = "\n\n".join(
            f"[{i+1}] {s['title']} ({s['url']})\n{s['content']}"
            for i, s in enumerate(sources)
        )
        summary = complete(
            system="You are a research assistant. Using ONLY the provided sources, "
                   "write a concise, factual answer to the user's query. Cite "
                   "sources inline as [1], [2], etc. If the sources are "
                   "insufficient, say so.",
            user=f"Query: {query}\n\nSources:\n{context}",
            max_tokens=900,
        )
    except LLMUnavailable:
        summary = None
    except Exception as exc:
        summary = f"(Could not synthesize summary: {exc})"

    return ok({
        "query": query,
        "summary": summary,
        "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
    })


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="web_search",
            description="Search the web for up-to-date information and return a list "
                        "of result titles, URLs and snippets.",
            category="Research",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "max_results": {"type": "integer", "description": "Max results (default 6)."},
                },
                "required": ["query"],
            },
            func=web_search,
        ),
        Tool(
            name="deep_web_search",
            description="Perform a deep web search: read the top result pages and "
                        "synthesize a concise, cited answer. Use for research "
                        "questions that need more than snippets.",
            category="Research",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research query."},
                    "max_results": {"type": "integer", "description": "Pages to read (default 5)."},
                },
                "required": ["query"],
            },
            func=deep_web_search,
        ),
    ]
