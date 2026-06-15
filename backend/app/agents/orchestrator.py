"""Multi-agent orchestrator.

Coordinates Trend Researcher -> Content Writer -> Verifier and emits progress events
that the API streams to the frontend so the user can watch the pipeline work.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from app.agents import content_writer, trend_researcher, verifier
from app.schemas import GenerateRequest

logger = logging.getLogger(__name__)


def _event(type_: str, **data: Any) -> dict:
    return {"type": type_, **data}


async def run_pipeline(req: GenerateRequest) -> AsyncGenerator[dict, None]:
    """Yield progress events; the final 'complete' event carries the full result."""
    try:
        # --- Stage 1: Trend research + deep search ---
        yield _event("agent_start", agent="researcher", label="Researching trending topics (last 24h)")
        research = await trend_researcher.run(req)
        yield _event(
            "agent_complete",
            agent="researcher",
            label="Found a trending angle",
            trending_topic=research.get("trending_topic"),
            rationale=research.get("rationale"),
            key_points=research.get("key_points", []),
        )
        # Surface sources early so the UI can show provenance while writing.
        yield _event("sources", sources=research.get("sources", []))

        # --- Stage 2: Writing ---
        yield _event("agent_start", agent="writer", label="Writing your content")
        draft = await content_writer.run(req, research)
        yield _event("agent_complete", agent="writer", label="Draft ready")

        # --- Stage 3: Verification / polish ---
        yield _event("agent_start", agent="verifier", label="Fact-checking and polishing")
        reviewed = await verifier.run(req, research, draft)
        verification = reviewed["verification"]
        content = reviewed["content"]
        yield _event(
            "agent_complete",
            agent="verifier",
            label="Verified",
            approved=verification.get("approved"),
            score=verification.get("score"),
        )

        result = {
            "trending_topic": research.get("trending_topic", ""),
            "sources": research.get("sources", []),
            "verification": verification,
            **content,
        }
        yield _event("complete", result=result)

    except Exception as exc:  # pragma: no cover
        logger.exception("Pipeline failed")
        yield _event("error", message=str(exc))
