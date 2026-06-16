"""Shared helpers for agents."""

from __future__ import annotations

from ..models import SearchResult


def format_sources(results: list[SearchResult], limit: int = 12) -> str:
    """Render search results into a compact, numbered context block for prompts."""
    lines = []
    for i, r in enumerate(results[:limit], start=1):
        lines.append(f"[{i}] {r.title}\nURL: {r.url}\n{r.content}".strip())
    return "\n\n".join(lines) if lines else "(no sources found)"
