"""Harvest recent articles from the configured RSS feeds.

Responsibilities (and nothing more):
  * pull each feed (with a browser-like request so sites don't 403 us),
  * keep only items published within the lookback window,
  * normalise them into :class:`Article` objects,
  * de-duplicate and cap the total.

We fetch the bytes ourselves with :mod:`urllib` instead of letting feedparser
do it, purely so we can see the real HTTP status. Many Indian news sites reject
the default Python/feedparser user-agent with ``403 Forbidden``; feedparser
swallows that and returns an empty feed, which otherwise looks indistinguishable
from "no recent news". Explicit status logging makes failures obvious.
"""

from __future__ import annotations

import html
import logging
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import feedparser

from .models import Article
from .sources import NewsSource

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")

# A realistic desktop-browser UA. The default feedparser UA is frequently
# blocked by The Hindu, Times of India, PIB, etc.
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-IN,en;q=0.9",
}


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


def _http_get(url: str, timeout: int) -> tuple[int | None, bytes | None, str | None]:
    """Fetch a URL with browser headers. Returns (status, body, error)."""
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), None
    except urllib.error.HTTPError as exc:
        return exc.code, None, f"HTTP {exc.code} {exc.reason}"
    except Exception as exc:  # URLError, timeout, SSL, etc.
        return None, None, f"{type(exc).__name__}: {exc}"


def _fetch_one(
    source: NewsSource, cutoff: datetime, timeout: int, keep_undated: bool
) -> list[Article]:
    """Fetch and filter a single feed. Never raises — logs and returns []."""
    status, body, error = _http_get(source.url, timeout)
    if body is None:
        logger.warning("%s: fetch failed (%s)", source.name, error)
        return []

    parsed = feedparser.parse(body)
    if parsed.bozo and not parsed.entries:
        logger.warning(
            "%s: HTTP %s but feed unparseable (%s)",
            source.name,
            status,
            getattr(parsed, "bozo_exception", "unknown error"),
        )
        return []

    now = datetime.now(timezone.utc)
    articles: list[Article] = []
    undated = 0
    for entry in parsed.entries:
        title = _clean(entry.get("title"))
        if not title:
            continue
        published = _parse_published(entry)
        if published is None:
            if not keep_undated:
                continue
            undated += 1
            published = now  # treat as fresh; feeds are recency-ordered
        elif published < cutoff:
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

    extra = f" ({undated} undated kept)" if undated else ""
    logger.info(
        "%s: HTTP %s, %d/%d entries in window%s",
        source.name,
        status,
        len(articles),
        len(parsed.entries),
        extra,
    )
    return articles


def fetch_recent_articles(
    sources: list[NewsSource],
    lookback_hours: int,
    max_articles: int,
    request_timeout: int = 20,
    keep_undated: bool = True,
) -> list[Article]:
    """Return de-duplicated, recency-sorted articles from all sources."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    collected: list[Article] = []
    # Feeds are independent and I/O bound -> fetch them concurrently.
    with ThreadPoolExecutor(max_workers=min(8, len(sources))) as pool:
        futures = {
            pool.submit(_fetch_one, src, cutoff, request_timeout, keep_undated): src
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
