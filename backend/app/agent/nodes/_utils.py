"""Shared helpers for agent nodes."""
from __future__ import annotations

import json
from typing import List

from ...schemas.source import Source


def parse_query_list(raw: str, fallback: str, n: int) -> List[str]:
    """Best-effort extraction of a JSON array of query strings from LLM output."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[-1] if "\n" in text else text
    try:
        start = text.index("[")
        end = text.rindex("]") + 1
        data = json.loads(text[start:end])
        queries = [str(q).strip() for q in data if str(q).strip()]
        if queries:
            return queries[:n]
    except (ValueError, json.JSONDecodeError):
        pass
    # Fallback: split on lines, else use the original query.
    lines = [ln.strip("-* 1234567890.").strip() for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln]
    return lines[:n] if lines else [fallback]


def dedupe_sources(sources: List[Source]) -> List[Source]:
    """Deduplicate sources by URL (falling back to title), preserving order."""
    seen = set()
    out: List[Source] = []
    for s in sources:
        key = s.url or s.title
        if key and key not in seen:
            seen.add(key)
            out.append(s)
    return out
