"""Content agent: expand an outline into fully written, laid-out slides."""

from __future__ import annotations

from typing import List

from ..llm import LLMClient
from ..models import Deck, Outline, ResearchFinding

_SYSTEM = (
    "You are a senior presentation designer and copywriter. Expand the given "
    "outline into a complete deck of slides.\n\n"
    "Rules:\n"
    "- Open with a TITLE slide and end with a CLOSING slide.\n"
    "- Choose a varied, sensible layout for each content slide from: "
    "bullets, two_column, quote, metrics, section.\n"
    "- Use a 'metrics' slide when you have 2-3 strong numbers; a 'quote' "
    "slide for a memorable statement; 'two_column' to compare or contrast.\n"
    "- Bullets are tight: max 6 per slide, max ~12 words each, no trailing "
    "periods, parallel phrasing.\n"
    "- Ground every claim in the source/research. Do NOT fabricate "
    "statistics; only use numbers present in the material.\n"
    "- Write concise speaker notes for each slide.\n"
    "- Keep the author as 'DeckForge' unless the source names a presenter."
)


def _format_findings(findings: List[ResearchFinding]) -> str:
    if not findings:
        return "(none)"
    return "\n".join(
        f"- {f.claim} [{f.source_title or ''} {f.source_url or ''}]".strip()
        for f in findings
    )


class ContentAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(
        self,
        outline: Outline,
        source: str,
        findings: List[ResearchFinding],
        *,
        theme: str,
    ) -> Deck:
        sections = "\n".join(f"{i+1}. {s}" for i, s in enumerate(outline.sections))
        user = (
            f"DECK TITLE: {outline.title}\n"
            f"SUBTITLE: {outline.subtitle}\n\n"
            f"SECTIONS TO COVER:\n{sections}\n\n"
            f"SOURCE MATERIAL:\n{source}\n\n"
            f"RESEARCH FINDINGS:\n{_format_findings(findings)}"
        )
        deck = self._llm.complete_model(Deck, _SYSTEM, user)
        # The renderer owns theming; pin it regardless of what the model said.
        deck.theme = theme
        if not deck.title:
            deck.title = outline.title
        return deck
