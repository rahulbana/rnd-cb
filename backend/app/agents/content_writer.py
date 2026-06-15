"""Content Writer agent.

Writes the full deliverable (title, body, description, keywords, hashtags) grounded
in the research provided by the Trend Researcher agent.
"""
from __future__ import annotations

import logging

from app.agents.base import complete_json
from app.config import settings
from app.schemas import GenerateRequest

logger = logging.getLogger(__name__)

LENGTH_GUIDE = {
    "short": "about 150-250 words",
    "medium": "about 400-600 words",
    "long": "about 900-1200 words",
}

PLATFORM_GUIDE = {
    "linkedin": (
        "Write a LinkedIn post: a strong scroll-stopping hook on the first line, short "
        "punchy paragraphs, line breaks for readability, and a closing question or CTA. "
        "Use markdown only sparingly."
    ),
    "website": (
        "Write a website article in clean markdown with an H1 title handled separately, "
        "logical H2 sections, and scannable paragraphs."
    ),
    "blog": (
        "Write a blog post in markdown with an engaging intro, H2 sections, examples, and "
        "a concluding takeaway."
    ),
}

SYSTEM = """You are an expert content writer and SEO strategist. Write original,
accurate, engaging content grounded ONLY in the supplied research and sources.
Do not invent statistics. Match the requested tone, length, and platform style.

Return strict JSON with this shape:
{
  "title": "compelling title",
  "body": "the full content (markdown allowed, no top-level H1)",
  "description": "a 1-2 sentence meta description (<= 160 chars)",
  "keywords": ["5-10 SEO keywords"],
  "hashtags": ["5-10 hashtags WITHOUT spaces, including the # symbol"]
}"""


async def run(req: GenerateRequest, research: dict) -> dict:
    if not settings.has_openai:
        return _fallback(req, research)

    sources_text = _format_sources(research.get("sources", []))
    key_points = "\n".join(f"- {p}" for p in research.get("key_points", []))

    user = f"""Trending angle: {research.get('trending_topic')}
Why it's timely: {research.get('rationale', '')}

Platform: {req.platform.value} — {PLATFORM_GUIDE.get(req.platform.value, '')}
Tone: {req.tone.value}
Length: {LENGTH_GUIDE.get(req.length.value, 'about 400-600 words')}
Target audience: {req.audience or 'general professional audience'}
Extra writer preferences: {req.preferences or '(none)'}

Key points to cover:
{key_points or '(use your judgement based on sources)'}

Research sources (ground the content in these — cite facts only from here):
{sources_text}

Write the deliverable now."""

    result = await complete_json(system=SYSTEM, user=user, model=settings.openai_model, temperature=0.8)

    return {
        "title": (result.get("title") or research.get("trending_topic") or "Untitled").strip(),
        "body": (result.get("body") or "").strip(),
        "description": (result.get("description") or "").strip(),
        "keywords": _clean_list(result.get("keywords", [])),
        "hashtags": _clean_hashtags(result.get("hashtags", [])),
    }


def _format_sources(sources: list[dict]) -> str:
    if not sources:
        return "(no sources available)"
    lines = []
    for i, s in enumerate(sources[:10], 1):
        lines.append(f"[{i}] {s.get('title')} ({s.get('url')})\n    {s.get('snippet', '')[:240]}")
    return "\n".join(lines)


def _clean_list(items) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(i).strip() for i in items if str(i).strip()][:10]


def _clean_hashtags(items) -> list[str]:
    out = []
    for i in _clean_list(items):
        tag = i if i.startswith("#") else f"#{i}"
        out.append(tag.replace(" ", ""))
    return out


def _fallback(req: GenerateRequest, research: dict) -> dict:
    topic = research.get("trending_topic", req.topic or "your topic")
    points = research.get("key_points", [])
    body = f"# (Demo output)\n\nThis article about **{topic}** was generated without an OpenAI key.\n\n"
    body += "\n".join(f"- {p}" for p in points)
    return {
        "title": f"{topic}",
        "body": body,
        "description": f"An overview of {topic}.",
        "keywords": [topic.lower(), req.platform.value, req.tone.value],
        "hashtags": [f"#{topic.split()[0].lower()}" if topic else "#content", "#contentmarketing"],
    }
