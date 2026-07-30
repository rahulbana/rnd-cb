"""Deep web research: plan queries, search the live web, collect real sources.

Providers:
  * ``openai`` (default) — uses OpenAI's built-in web_search tool, no extra
    key beyond OPENAI_API_KEY.
  * ``tavily``           — uses the Tavily Search API (needs TAVILY_API_KEY).
  * ``none``             — disables research.

Failures are non-fatal: research degrades gracefully so a transient search
error never blocks content generation.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from app.core.config import settings
from app.schemas.generation import Source

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    findings: str = ""
    sources: list[Source] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)


def _openai_client():
    from app.services.observability import get_openai_client

    return get_openai_client(
        api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL
    )


# --- Query planning --------------------------------------------------

def _plan_queries(prompt: str, max_queries: int) -> list[str]:
    """Break the brief into focused web search queries."""
    if max_queries <= 1:
        return [prompt]
    try:
        client = _openai_client()
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You plan web research. Given a writing brief, return "
                        "focused, diverse search engine queries that together "
                        "cover the facts, context and recent developments a "
                        "writer would need. Respond as JSON: "
                        '{"queries": ["...", "..."]}.'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Brief: {prompt}\nReturn up to {max_queries} queries.",
                },
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(completion.choices[0].message.content or "{}")
        queries = [q for q in data.get("queries", []) if isinstance(q, str) and q.strip()]
        return queries[:max_queries] or [prompt]
    except Exception as exc:  # pragma: no cover
        logger.warning("Query planning failed (%s); using the raw prompt.", exc)
        return [prompt]


# --- Search backends -------------------------------------------------

def _openai_web_search(query: str) -> tuple[str, list[Source]]:
    """Run one web search via OpenAI's built-in tool and collect citations."""
    client = _openai_client()
    # Tool name changed across API versions; try the known variants.
    last_exc: Exception | None = None
    for tool_type in ("web_search_preview", "web_search"):
        try:
            resp = client.responses.create(
                model=settings.WEB_SEARCH_MODEL,
                tools=[{"type": tool_type}],
                input=(
                    "Research this and answer with key, verifiable facts and "
                    f"figures, citing sources: {query}"
                ),
            )
            return _parse_openai_response(resp)
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            continue
    raise RuntimeError(f"OpenAI web search failed: {last_exc}")


def _parse_openai_response(resp) -> tuple[str, list[Source]]:
    text = getattr(resp, "output_text", "") or ""
    sources: list[Source] = []
    for item in getattr(resp, "output", []) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", []) or []:
            for ann in getattr(content, "annotations", []) or []:
                if getattr(ann, "type", None) == "url_citation":
                    url = getattr(ann, "url", None)
                    if url:
                        sources.append(
                            Source(
                                title=getattr(ann, "title", None) or url,
                                url=url,
                                type="website",
                            )
                        )
    return text, sources


def _tavily_search(query: str) -> tuple[str, list[Source]]:
    import httpx

    if not settings.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY not configured")
    resp = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "max_results": settings.WEB_SEARCH_MAX_RESULTS,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    findings = data.get("answer") or ""
    sources = [
        Source(title=r.get("title") or r.get("url"), url=r.get("url"), type="website")
        for r in data.get("results", [])
        if r.get("url")
    ]
    # Include a short excerpt from each result in the findings text.
    snippets = "\n".join(
        f"- {r.get('title')}: {(r.get('content') or '')[:400]}"
        for r in data.get("results", [])
    )
    return f"{findings}\n{snippets}".strip(), sources


def _search(query: str) -> tuple[str, list[Source]]:
    provider = settings.WEB_SEARCH_PROVIDER.lower()
    if provider == "tavily":
        return _tavily_search(query)
    return _openai_web_search(query)


# --- Orchestration ---------------------------------------------------

def deep_research(prompt: str, depth: str = "deep") -> ResearchResult:
    """Run web research for a brief and return grounded findings + sources."""
    if settings.WEB_SEARCH_PROVIDER.lower() == "none":
        return ResearchResult()
    if settings.WEB_SEARCH_PROVIDER.lower() == "openai" and not settings.OPENAI_API_KEY:
        logger.warning("Web search requested but OPENAI_API_KEY is not set.")
        return ResearchResult()

    max_queries = settings.DEEP_RESEARCH_MAX_QUERIES if depth == "deep" else 1
    queries = _plan_queries(prompt, max_queries)

    findings_parts: list[str] = []
    sources: list[Source] = []
    seen_urls: set[str] = set()

    for q in queries:
        try:
            text, found = _search(q)
        except Exception as exc:  # pragma: no cover
            logger.warning("Web search failed for %r (%s)", q, exc)
            continue
        if text:
            findings_parts.append(f"### Research: {q}\n{text}")
        for s in found:
            key = (s.url or s.title or "").lower()
            if key and key not in seen_urls:
                seen_urls.add(key)
                sources.append(s)

    return ResearchResult(
        findings="\n\n".join(findings_parts).strip(),
        sources=sources,
        queries=queries,
    )
