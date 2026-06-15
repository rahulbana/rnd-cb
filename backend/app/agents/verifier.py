"""Verifier agent.

Reviews the drafted content for factual grounding against the sources, tone/length
fit, and overall quality. Returns an approval decision plus a polished final version.
"""
from __future__ import annotations

import logging

from app.agents.base import complete_json
from app.config import settings
from app.schemas import GenerateRequest

logger = logging.getLogger(__name__)

SYSTEM = """You are a meticulous editor and fact-checker. Review the draft against
the provided sources and the requested tone/platform. Check that claims are grounded
in the sources, the tone fits, and there are no obvious errors. Lightly polish the
content but do not invent new facts.

Return strict JSON with this shape:
{
  "approved": true/false,
  "score": 0-100,
  "issues": ["any problems found, empty if none"],
  "notes": "short summary of your review",
  "final": {
    "title": "...",
    "body": "...",
    "description": "...",
    "keywords": ["..."],
    "hashtags": ["#..."]
  }
}"""


async def run(req: GenerateRequest, research: dict, draft: dict) -> dict:
    """Return {verification: {...}, content: {...}} with the (possibly polished) final."""
    if not settings.has_openai:
        return {
            "verification": {
                "approved": True,
                "score": 0.0,
                "issues": ["OpenAI key not configured — verification skipped."],
                "notes": "Demo mode.",
            },
            "content": draft,
        }

    sources_text = "\n".join(
        f"[{i}] {s.get('title')} ({s.get('url')})" for i, s in enumerate(research.get("sources", [])[:10], 1)
    )
    user = f"""Platform: {req.platform.value} | Tone: {req.tone.value} | Length: {req.length.value}

Sources:
{sources_text or '(none)'}

Draft to review:
Title: {draft.get('title')}
Description: {draft.get('description')}
Keywords: {', '.join(draft.get('keywords', []))}
Hashtags: {' '.join(draft.get('hashtags', []))}

Body:
{draft.get('body')}

Review and return the final polished version."""

    result = await complete_json(system=SYSTEM, user=user, model=settings.openai_model, temperature=0.3)

    final = result.get("final") or {}
    content = {
        "title": (final.get("title") or draft.get("title", "")).strip(),
        "body": (final.get("body") or draft.get("body", "")).strip(),
        "description": (final.get("description") or draft.get("description", "")).strip(),
        "keywords": final.get("keywords") or draft.get("keywords", []),
        "hashtags": final.get("hashtags") or draft.get("hashtags", []),
    }
    raw_score = result.get("score", 0)
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = 0.0

    verification = {
        "approved": bool(result.get("approved", True)),
        "score": score,
        "issues": result.get("issues", []) if isinstance(result.get("issues"), list) else [],
        "notes": result.get("notes", ""),
    }
    return {"verification": verification, "content": content}
