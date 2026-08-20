"""Optional web research step using OpenAI's web-search capability.

After the document text is extracted, this module asks a search-enabled OpenAI
model to find authoritative, curriculum-aligned reference material online — from
reputable sources such as education boards/school syllabi, well-known coaching
centres, and trusted educational sites. The gathered context (and its source
URLs) is then fed into notes/question generation to add depth and standard
exam-style coverage.

Only the extracted document text is sent — never the original file. Failures are
non-fatal: if search is unavailable, generation proceeds without it.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List

from .llm import _client

# A search-enabled model. OpenAI's *-search-preview models run web search
# server-side and return answers with citations.
SEARCH_MODEL = os.getenv("OPENAI_SEARCH_MODEL", "gpt-4o-mini-search-preview")

# Whether the research step runs at all (can be forced off globally).
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() not in (
    "0", "false", "no", "off",
)

# How much of the document to use when forming the research query.
RESEARCH_MAX_CHARS = int(os.getenv("RESEARCH_MAX_CHARS", "6000"))
MAX_SOURCES = int(os.getenv("RESEARCH_MAX_SOURCES", "8"))

_URL_RE = re.compile(r"https?://[^\s)\]>\"']+")


@dataclass
class ResearchResult:
    context: str = ""
    sources: List[str] = field(default_factory=list)
    used: bool = False


def is_enabled() -> bool:
    return ENABLE_WEB_SEARCH and bool(os.getenv("OPENAI_API_KEY"))


def gather_references(text: str, grade_level: str = "") -> ResearchResult:
    """Search the web for reference material related to ``text``.

    Returns an empty (used=False) result on any failure so callers can proceed.
    """
    if not is_enabled():
        return ResearchResult()

    excerpt = text[:RESEARCH_MAX_CHARS]
    audience = f" The student's level is {grade_level}." if grade_level else ""

    prompt = f"""You are a study-material researcher for students and parents.
A student is studying the topic in the material below.{audience}

Use web search to find authoritative, curriculum-aligned reference material from
reputable sources — education boards / school syllabi, well-known coaching
centres, and trusted educational websites. Gather:
- Additional key facts, definitions, and clarifications relevant to this topic
- Points and sub-topics that are commonly tested in exams
- Typical exam-style question patterns for this topic

Write a concise briefing (about 250-400 words) that a teacher could use to
enrich notes and questions. Be accurate and do not invent facts or sources.
At the very end, add a line exactly "SOURCES:" followed by the source URLs you
actually used, one per line.

=== MATERIAL START ===
{excerpt}
=== MATERIAL END ==="""

    try:
        client = _client()
        response = client.chat.completions.create(
            model=SEARCH_MODEL,
            messages=[{"role": "user", "content": prompt}],
            # Enable server-side web search; sent via extra_body for broad SDK
            # compatibility.
            extra_body={"web_search_options": {}},
        )
        message = response.choices[0].message
        content = message.content or ""
    except Exception:
        # Search model unavailable / network / auth: degrade gracefully.
        return ResearchResult()

    sources = _extract_sources(message, content)
    context = _strip_sources_block(content).strip()
    if not context and not sources:
        return ResearchResult()
    return ResearchResult(context=context, sources=sources, used=True)


def _extract_sources(message, content: str) -> List[str]:
    urls: List[str] = []

    # 1) Structured citations, when the SDK/model provides them.
    annotations = getattr(message, "annotations", None) or []
    for ann in annotations:
        url = None
        if isinstance(ann, dict):
            url = (ann.get("url_citation") or {}).get("url") or ann.get("url")
        else:
            citation = getattr(ann, "url_citation", None)
            url = getattr(citation, "url", None) or getattr(ann, "url", None)
        if url:
            urls.append(url)

    # 2) URLs listed in a trailing SOURCES: block or inline in the text.
    block = _sources_block(content)
    for match in _URL_RE.findall(block or content):
        urls.append(match.rstrip(".,);"))

    # De-duplicate, preserve order, cap.
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= MAX_SOURCES:
            break
    return out


def _sources_block(content: str) -> str:
    idx = content.rfind("SOURCES:")
    return content[idx + len("SOURCES:"):] if idx != -1 else ""


def _strip_sources_block(content: str) -> str:
    idx = content.rfind("SOURCES:")
    return content[:idx] if idx != -1 else content
