"""Design agent: enforce structural polish and choose a fitting theme.

This agent does the deterministic "art direction" pass that you don't want
to trust an LLM to get pixel-perfect: guaranteeing a cover and closing
slide, trimming overflowing bullets, and (optionally) auto-selecting a
colour theme that matches the subject matter.
"""

from __future__ import annotations

from ..llm import LLMClient
from ..models import Deck, Slide, SlideLayout
from ..deck.themes import THEMES

_MAX_BULLETS = 6
_MAX_BULLET_WORDS = 14

_THEME_SYSTEM = (
    "You pick a visual theme for a presentation based on its tone. Reply with "
    "exactly one of these theme names and nothing else: " + ", ".join(THEMES)
)


class DesignAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def _auto_theme(self, deck: Deck) -> str:
        try:
            choice = self._llm.complete(
                _THEME_SYSTEM,
                f"Title: {deck.title}\nSubtitle: {deck.subtitle}",
                fast=True,
                temperature=0.0,
            ).strip().lower()
        except Exception:  # noqa: BLE001
            choice = ""
        return choice if choice in THEMES else "midnight"

    @staticmethod
    def _trim_bullets(bullets: list[str]) -> list[str]:
        cleaned = []
        for b in bullets[:_MAX_BULLETS]:
            words = b.strip().rstrip(".").split()
            cleaned.append(" ".join(words[:_MAX_BULLET_WORDS]))
        return cleaned

    def run(self, deck: Deck, *, theme: str) -> Deck:
        # Resolve theme: explicit > auto-detect > fallback.
        resolved = theme.lower()
        if resolved == "auto":
            resolved = self._auto_theme(deck)
        elif resolved not in THEMES:
            resolved = "midnight"
        deck.theme = resolved

        # Tidy every slide's bullet content.
        for slide in deck.slides:
            slide.bullets = self._trim_bullets(slide.bullets)
            slide.column_b = self._trim_bullets(slide.column_b)

        # Guarantee a cover slide.
        if not deck.slides or deck.slides[0].layout != SlideLayout.TITLE:
            deck.slides.insert(
                0,
                Slide(
                    layout=SlideLayout.TITLE,
                    title=deck.title,
                    subtitle=deck.subtitle,
                ),
            )

        # Guarantee a closing slide.
        if deck.slides[-1].layout != SlideLayout.CLOSING:
            deck.slides.append(
                Slide(
                    layout=SlideLayout.CLOSING,
                    title="Thank You",
                    subtitle=deck.subtitle or "Questions & discussion",
                )
            )

        return deck
