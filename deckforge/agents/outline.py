"""Outline agent: turn raw source + research into a presentation skeleton."""

from __future__ import annotations

from typing import List

from ..llm import LLMClient
from ..models import Outline, ResearchFinding

_SYSTEM = (
    "You are a world-class presentation strategist. From the provided source "
    "material (and optional research findings) you design the narrative arc "
    "of a deck: a compelling title, a one-line subtitle, and an ordered list "
    "of 5-9 section headings that tell a coherent story (problem -> insight "
    "-> evidence -> recommendation -> next steps). Section headings are "
    "short, punchy, and specific to the content — never generic."
)


def _format_findings(findings: List[ResearchFinding]) -> str:
    if not findings:
        return "(no external research available)"
    return "\n".join(f"- {f.claim} [{f.source_url or 'n/a'}]" for f in findings)


class OutlineAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(
        self,
        topic: str,
        source: str,
        findings: List[ResearchFinding],
        *,
        target_slides: int,
    ) -> Outline:
        user = (
            f"Topic / instruction: {topic}\n"
            f"Target slide count: roughly {target_slides}\n\n"
            f"SOURCE MATERIAL:\n{source}\n\n"
            f"RESEARCH FINDINGS:\n{_format_findings(findings)}"
        )
        return self._llm.complete_model(Outline, _SYSTEM, user)
