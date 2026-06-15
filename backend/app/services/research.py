"""Best-effort web research used to ground quiz generation.

Before the quiz agent writes questions, it searches the web for board
materials (CBSE / ICSE / state boards), previous-year papers and teacher
notes/quizzes on the topic, and feeds short snippets to the model as
reference context.

Two providers are supported, picked automatically:
  1. Tavily  — used when TAVILY_API_KEY is set (higher quality).
  2. DuckDuckGo — no API key required (via the `ddgs`/`duckduckgo_search` pkg).

Everything here is defensive: any failure (no network, missing package,
timeout) returns an empty context so plan generation continues normally.
"""
from __future__ import annotations

import asyncio
import json
import urllib.request

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("services.research")


def _queries(grade: int, subject: str, topic: str) -> list[str]:
    return [
        f"CBSE class {grade} {subject} {topic} previous year question paper",
        f"ICSE class {grade} {subject} {topic} important questions and answers",
        f"{subject} {topic} class {grade} quiz notes by teachers",
    ]


def _tavily_search(api_key: str, queries: list[str], per_query: int) -> list[dict]:
    results: list[dict] = []
    for q in queries:
        payload = json.dumps(
            {
                "api_key": api_key,
                "query": q,
                "max_results": per_query,
                "search_depth": "basic",
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            for r in data.get("results", []):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "snippet": r.get("content", ""),
                        "url": r.get("url", ""),
                    }
                )
        except Exception:  # noqa: BLE001 - best-effort per query
            continue
    return results


def _ddg_search(queries: list[str], per_query: int) -> list[dict]:
    try:
        from ddgs import DDGS  # maintained successor package
    except Exception:
        try:
            from duckduckgo_search import DDGS  # older package name
        except Exception:
            return []

    results: list[dict] = []
    try:
        with DDGS() as ddgs:
            for q in queries:
                try:
                    for r in ddgs.text(q, max_results=per_query):
                        results.append(
                            {
                                "title": r.get("title", ""),
                                "snippet": r.get("body", ""),
                                "url": r.get("href", ""),
                            }
                        )
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        return results
    return results


def _format(results: list[dict], limit: int = 10) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for r in results:
        snippet = (r.get("snippet") or "").strip().replace("\n", " ")
        title = (r.get("title") or "").strip()
        if not snippet or title in seen:
            continue
        seen.add(title)
        url = r.get("url", "")
        lines.append(f"- {title}: {snippet[:280]} ({url})")
        if len(lines) >= limit:
            break
    return "\n".join(lines)


def _research_sync(grade: int, subject: str, topic: str) -> str:
    settings = get_settings()
    queries = _queries(grade, subject, topic)
    per_query = settings.research_max_results
    if settings.tavily_api_key:
        results = _tavily_search(settings.tavily_api_key, queries, per_query)
        if not results:  # fall back to DDG if Tavily yielded nothing
            results = _ddg_search(queries, per_query)
    else:
        results = _ddg_search(queries, per_query)
    return _format(results)


async def research_quiz_context(grade: int, subject: str, topic: str) -> str:
    """Return reference snippets for the quiz agent, or '' if unavailable."""
    settings = get_settings()
    if not settings.web_research:
        return ""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_research_sync, grade, subject, topic),
            timeout=settings.research_timeout,
        )
    except Exception:  # noqa: BLE001 - research is strictly best-effort
        log.warning("web research unavailable; continuing without references")
        return ""
