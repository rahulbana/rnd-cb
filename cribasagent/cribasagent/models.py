"""Shared data structures passed between the pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    """A single news item harvested from a feed."""

    title: str
    summary: str
    link: str
    source: str
    section: str
    published: datetime  # timezone-aware (UTC)

    def as_prompt_block(self) -> str:
        """Compact representation handed to the LLM (token-friendly)."""
        body = self.summary.strip()
        if len(body) > 600:
            body = body[:600].rstrip() + "…"
        return f"- [{self.source}] {self.title.strip()}\n  {body}"


@dataclass
class Brief:
    """The structured output of the summarisation stage."""

    generated_at: datetime
    article_count: int
    source_count: int
    # subject -> list of exam-ready bullet points
    sections: dict[str, list[str]] = field(default_factory=dict)
