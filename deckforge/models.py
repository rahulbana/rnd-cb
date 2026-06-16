"""Typed data contracts shared across agents and the renderer.

Keeping these as Pydantic models means every hand-off between agents is
validated, and the LLM's JSON output is coerced into a known shape before it
ever reaches the PowerPoint builder.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SlideLayout(str, Enum):
    """Visual templates the renderer knows how to draw."""

    TITLE = "title"          # Cover slide
    SECTION = "section"      # Section divider
    BULLETS = "bullets"      # Title + bullet list
    TWO_COLUMN = "two_column"  # Two side-by-side bullet columns
    QUOTE = "quote"          # Large pull-quote
    METRICS = "metrics"      # Up to 3 big stat callouts
    CLOSING = "closing"      # Thank-you / call to action


class Metric(BaseModel):
    """A single headline statistic for a METRICS slide."""

    value: str = Field(..., description="The big number, e.g. '42%' or '$1.2M'.")
    label: str = Field(..., description="Short caption under the value.")


class Slide(BaseModel):
    """One rendered slide."""

    layout: SlideLayout = SlideLayout.BULLETS
    title: str = ""
    subtitle: str = ""
    bullets: List[str] = Field(default_factory=list)
    column_b: List[str] = Field(default_factory=list)
    quote: str = ""
    attribution: str = ""
    metrics: List[Metric] = Field(default_factory=list)
    notes: str = Field(default="", description="Speaker notes.")


class Deck(BaseModel):
    """A complete presentation prior to rendering."""

    title: str
    subtitle: str = ""
    author: str = "DeckForge"
    theme: str = "midnight"
    slides: List[Slide] = Field(default_factory=list)


class ResearchFinding(BaseModel):
    """A single distilled fact gathered by the research agent."""

    claim: str
    source_url: Optional[str] = None
    source_title: Optional[str] = None


class Outline(BaseModel):
    """The structural plan the content agent fills in."""

    title: str
    subtitle: str = ""
    sections: List[str] = Field(default_factory=list)
