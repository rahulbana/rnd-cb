"""News headlines via Google News RSS (free, no key)."""
from __future__ import annotations

from urllib.parse import quote_plus

import feedparser

from .base import Tool, ok

RSS_TOPIC = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
RSS_SEARCH = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def get_news_headlines(topic: str | None = None, limit: int = 10) -> dict:
    """Return current news headlines, optionally for a search topic/keyword."""
    url = RSS_SEARCH.format(q=quote_plus(topic)) if topic else RSS_TOPIC
    feed = feedparser.parse(url)
    entries = []
    for e in feed.entries[:limit]:
        entries.append({
            "title": e.get("title"),
            "link": e.get("link"),
            "published": e.get("published"),
            "source": (e.get("source", {}) or {}).get("title")
            if isinstance(e.get("source"), dict) else e.get("source"),
        })
    return ok({
        "topic": topic or "top stories",
        "count": len(entries),
        "headlines": entries,
    })


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="get_news_headlines",
            description="Get current news headlines. Optionally provide a topic or "
                        "keyword to search for specific news.",
            category="Research",
            parameters={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Optional topic/keyword."},
                    "limit": {"type": "integer", "description": "Max headlines (default 10)."},
                },
                "required": [],
            },
            func=get_news_headlines,
        )
    ]
