"""Harvest recent articles from the configured RSS feeds.

Responsibilities (and nothing more):
  * pull each feed,
  * keep only items published within the lookback window,
  * normalise them into :class:`Article` objects,
  * de-duplicate and cap the total.
"""

from __future__ import annotations

import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import feedparser

from .models import Article
from .sources import NewsSource

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    """Strip HTML tags and unescape entities from a feed summary."""
    if not text:
        return ""
    return html.unescape(_TAG_RE.sub(" ", text)).strip()


def _parse_published(entry) -> datetime | None:
    """Return a timezone-aware UTC datetime for an entry, or ``None``."""
    for key in ("published_parsed", "updated_parsed"):
        struct = entry.get(key)
        if struct:
            return datetime(*struct[:6], tzinfo=timezone.utc)
    return None


def _fetch_one(source: NewsSource, cutoff: datetime, timeout: int) -> list[Article]:
    """Fetch and filter a single feed. Never raises — logs and returns []."""
    try:
        # feedparser has no timeout arg; rely on the socket default set by caller.
        parsed = feedparser.parse(source.url)
    except Exception as exc:  # pragma: no cover - network/parse robustness
        logger.warning("Failed to fetch %s: %s", source.name, exc)
        return []

    articles: list[Article] = []
    for entry in parsed.entries:
        published = _parse_published(entry)
        if published is None or published < cutoff:
            continue
        title = _clean(entry.get("title"))
        if not title:
            continue
        articles.append(
            Article(
                title=title,
                summary=_clean(entry.get("summary") or entry.get("description")),
                link=entry.get("link", ""),
                source=source.name,
                section=source.section,
                published=published,
            )
        )
    logger.info("%s: %d articles in window", source.name, len(articles))
    return articles


def fetch_recent_articles(
    sources: list[NewsSource],
    lookback_hours: int,
    max_articles: int,
    request_timeout: int = 20,
) -> list[Article]:
    """Return de-duplicated, recency-sorted articles from all sources."""
    import socket

    socket.setdefaulttimeout(request_timeout)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    collected: list[Article] = []
    # Feeds are independent and I/O bound -> fetch them concurrently.
    with ThreadPoolExecutor(max_workers=min(8, len(sources))) as pool:
        futures = {
            pool.submit(_fetch_one, src, cutoff, request_timeout): src
            for src in sources
        }
        for future in as_completed(futures):
            collected.extend(future.result())

    deduped = _dedupe(collected)
    deduped.sort(key=lambda a: a.published, reverse=True)
    if len(deduped) > max_articles:
        logger.info("Capping %d -> %d articles", len(deduped), max_articles)
        deduped = deduped[:max_articles]
    return deduped


def _dedupe(articles: list[Article]) -> list[Article]:
    """Drop duplicates by link, then by a normalised title key."""
    seen_links: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[Article] = []
    for art in articles:
        link_key = art.link.split("?")[0].rstrip("/")
        title_key = re.sub(r"\W+", "", art.title.lower())[:80]
        if link_key and link_key in seen_links:
            continue
        if title_key in seen_titles:
            continue
        seen_links.add(link_key)
        seen_titles.add(title_key)
        unique.append(art)
    return unique
