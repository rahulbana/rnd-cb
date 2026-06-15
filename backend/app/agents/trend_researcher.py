"""Trend Researcher agent.

Discovers a trending angle from the last ~24 hours based on the user's seed topic
and preferences, then performs a deeper search to collect citable sources.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.base import complete_json
from app.agents.tools.web_search import web_search
from app.config import settings
from app.schemas import GenerateRequest

logger = logging.getLogger(__name__)

SYSTEM = """You are a Trend Research agent for a content marketing team.
You are given the latest web search results (titles + snippets) and a user's
interests. Identify the single most compelling, *currently trending* angle to
write about. Prefer fresh, specific angles over generic evergreen topics.

Return strict JSON with this shape:
{
  "trending_topic": "a concise, specific headline-style angle",
  "rationale": "1-2 sentences on why this is timely and relevant now",
  "key_points": ["3-6 concrete points the article should cover"],
  "search_queries": ["2-3 follow-up queries to gather supporting sources"]
}"""


async def run(req: GenerateRequest) -> dict:
    """Return {trending_topic, rationale, key_points, sources}."""
    seed = req.topic.strip() or req.audience.strip() or "industry trends"

    # 1) Broad discovery search restricted to recent results.
    discovery_query = f"latest trending news and discussions about {seed}"
    discovery = await web_search(discovery_query, recent_only=True)

    if not settings.has_openai:
        return _fallback(seed, discovery)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results_text = _format_results(discovery)
    user = f"""Today is {today}.
User seed topic: {seed or "(none — choose a strong trend)"}
Target platform: {req.platform.value}
Target audience: {req.audience or "general professional audience"}
Extra preferences: {req.preferences or "(none)"}

Recent web results from the last 24h:
{results_text}

Pick the best trending angle and follow-up search queries."""

    plan = await complete_json(
        system=SYSTEM,
        user=user,
        model=settings.openai_research_model,
        temperature=0.5,
    )
    trending_topic = plan.get("trending_topic") or seed
    key_points = plan.get("key_points") or []
    follow_ups = plan.get("search_queries") or [trending_topic]

    # 2) Deep search: gather supporting sources for the chosen angle.
    sources: list[dict] = list(discovery)
    for q in follow_ups[:3]:
        sources.extend(await web_search(q))

    return {
        "trending_topic": trending_topic,
        "rationale": plan.get("rationale", ""),
        "key_points": key_points,
        "sources": _dedupe_sources(sources),
    }


def _format_results(results: list[dict]) -> str:
    if not results:
        return "(no results)"
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.get('title')} — {r.get('snippet', '')[:200]} ({r.get('url')})")
    return "\n".join(lines)


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for s in sources:
        url = s.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(s)
    return unique


def _fallback(seed: str, discovery: list[dict]) -> dict:
    return {
        "trending_topic": f"What's new in {seed}",
        "rationale": "Generated without an OpenAI key configured.",
        "key_points": [
            f"Overview of {seed}",
            "Recent developments",
            "Practical takeaways for the reader",
        ],
        "sources": _dedupe_sources(discovery),
    }
