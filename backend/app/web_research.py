"""Optional web research step using DuckDuckGo or Tavily.

After the document text is extracted, this module searches the web for
authoritative, curriculum-aligned reference material — from reputable sources
such as education boards/school syllabi, well-known coaching centres, and
trusted educational sites. The gathered snippets (and their source URLs) are
then fed into notes/question generation to add depth and standard exam-style
coverage.

Search provider is pluggable via ``SEARCH_PROVIDER``:
- ``duckduckgo`` (default): no API key required
- ``tavily``: requires ``TAVILY_API_KEY``

Only a short search query derived from the extracted text leaves the server for
the search provider — never the original file. Failures are non-fatal: if search
is unavailable, generation proceeds without it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List

# Provider + tuning ---------------------------------------------------------
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo").strip().lower()
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() not in (
    "0", "false", "no", "off",
)
RESEARCH_MAX_CHARS = int(os.getenv("RESEARCH_MAX_CHARS", "6000"))
MAX_SOURCES = int(os.getenv("RESEARCH_MAX_SOURCES", "8"))
MAX_RESULTS = int(os.getenv("RESEARCH_MAX_RESULTS", "6"))
DDG_REGION = os.getenv("DDG_REGION", "wt-wt")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Steer results toward study material.
_QUERY_SUFFIX = os.getenv("RESEARCH_QUERY_SUFFIX", "study notes important exam questions")

# Image search (for illustrating notes). Best-effort; disable via env.
ENABLE_IMAGE_SEARCH = os.getenv("ENABLE_IMAGE_SEARCH", "true").lower() not in (
    "0", "false", "no", "off",
)
# Prefer diagram-style, license-friendly images.
_IMAGE_QUERY_SUFFIX = os.getenv("IMAGE_QUERY_SUFFIX", "diagram")

# Proxy for the search HTTP clients (honours the environment's egress proxy).
_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or None


@dataclass
class ResearchResult:
    context: str = ""
    sources: List[str] = field(default_factory=list)
    used: bool = False
    provider: str = ""


def is_enabled() -> bool:
    if not ENABLE_WEB_SEARCH:
        return False
    if SEARCH_PROVIDER == "tavily":
        return bool(TAVILY_API_KEY)
    return True  # duckduckgo needs no key


def gather_references(text: str, grade_level: str = "") -> ResearchResult:
    """Search the web for reference material related to ``text``.

    Returns an empty (used=False) result on any failure so callers can proceed.
    """
    if not is_enabled():
        return ResearchResult()

    query = _build_query(text, grade_level)
    if not query:
        return ResearchResult()

    try:
        if SEARCH_PROVIDER == "tavily":
            results, answer = _search_tavily(query)
        else:
            results, answer = _search_duckduckgo(query)
    except Exception:
        return ResearchResult()

    if not results and not answer:
        return ResearchResult()

    context = _build_context(results, answer)
    sources = _dedupe([r["url"] for r in results if r.get("url")])
    return ResearchResult(
        context=context, sources=sources, used=True, provider=SEARCH_PROVIDER
    )


# --- query construction ----------------------------------------------------

def _build_query(text: str, grade_level: str) -> str:
    topic = _llm_query(text, grade_level) or _heuristic_query(text)
    if not topic:
        return ""
    parts = [topic]
    if grade_level:
        parts.append(grade_level)
    parts.append(_QUERY_SUFFIX)
    return " ".join(p for p in parts if p).strip()


def _llm_query(text: str, grade_level: str) -> str:
    """Use the generation LLM to distill a concise search topic (best-effort)."""
    if not os.getenv("OPENAI_API_KEY"):
        return ""
    try:
        from .llm import MODEL, _client

        excerpt = text[:RESEARCH_MAX_CHARS]
        resp = _client().chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Read the study material below and return ONLY a short web "
                        "search query (max 10 words) naming its main subject/topic. "
                        "No quotes, no punctuation, no explanation.\n\n" + excerpt
                    ),
                }
            ],
            temperature=0,
            max_tokens=30,
        )
        return (resp.choices[0].message.content or "").strip().strip('"').replace("\n", " ")
    except Exception:
        return ""


def _heuristic_query(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if len(line) >= 8:
            return line[:120]
    return text.strip()[:120]


# --- providers -------------------------------------------------------------

def _search_duckduckgo(query: str):
    from ddgs import DDGS

    kwargs: Dict = {}
    if _PROXY:
        kwargs["proxy"] = _PROXY
    with DDGS(**kwargs) as ddgs:
        raw = list(ddgs.text(query, region=DDG_REGION, max_results=MAX_RESULTS))

    results = []
    for r in raw:
        url = r.get("href") or r.get("url") or r.get("link") or ""
        results.append(
            {
                "title": r.get("title") or "",
                "url": url,
                "snippet": r.get("body") or r.get("snippet") or r.get("description") or "",
            }
        )
    return results, ""


def _search_tavily(query: str):
    from tavily import TavilyClient

    client = TavilyClient(api_key=TAVILY_API_KEY)
    resp = client.search(
        query,
        max_results=MAX_RESULTS,
        include_answer=True,
        search_depth="basic",
    )
    results = []
    for r in resp.get("results", []) or []:
        results.append(
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "snippet": r.get("content") or "",
            }
        )
    return results, (resp.get("answer") or "")


# --- context assembly ------------------------------------------------------

def _build_context(results: List[dict], answer: str) -> str:
    lines: List[str] = []
    if answer:
        lines.append(f"Summary from search: {answer.strip()}")
        lines.append("")
    for r in results:
        title = (r.get("title") or "").strip()
        snippet = " ".join((r.get("snippet") or "").split())[:400]
        url = r.get("url") or ""
        if not (title or snippet):
            continue
        lines.append(f"- {title}: {snippet} ({url})")
    return "\n".join(lines).strip()


def images_enabled() -> bool:
    return ENABLE_IMAGE_SEARCH


def find_image(query: str) -> dict:
    """Return {"url", "source", "title"} for a query, or {} on any failure.

    Uses DuckDuckGo image search (no API key). Best-effort and safe-search on.
    """
    if not (ENABLE_IMAGE_SEARCH and query.strip()):
        return {}
    try:
        from ddgs import DDGS

        kwargs: Dict = {}
        if _PROXY:
            kwargs["proxy"] = _PROXY
        q = f"{query.strip()} {_IMAGE_QUERY_SUFFIX}".strip()
        with DDGS(**kwargs) as ddgs:
            raw = list(ddgs.images(q, region=DDG_REGION, safesearch="on", max_results=5))
    except Exception:
        return {}

    for r in raw:
        url = r.get("image") or r.get("url") or ""
        # Prefer direct image URLs that browsers can render inline.
        if url.lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
            return {
                "url": url,
                "source": r.get("url") or r.get("source") or "",
                "title": r.get("title") or "",
            }
    # Fall back to the first result even without a clean extension.
    if raw:
        r = raw[0]
        return {
            "url": r.get("image") or "",
            "source": r.get("url") or "",
            "title": r.get("title") or "",
        }
    return {}


def _dedupe(urls: List[str]) -> List[str]:
    seen, out = set(), []
    for u in urls:
        u = u.rstrip(".,);")
        if u and u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= MAX_SOURCES:
            break
    return out
