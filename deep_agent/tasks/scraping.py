"""Celery scraping task with Tenacity-backed resilience.

``scrape_url`` fetches a page, strips boilerplate and returns a
:class:`ScrapedDocument`.  Network fetches are retried with exponential
back-off via the shared :func:`http_retry` policy.
"""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from deep_agent.config import get_settings
from deep_agent.models.schemas import ScrapedDocument
from deep_agent.tasks.celery_app import celery_app
from deep_agent.utils.logging import get_logger
from deep_agent.utils.politeness import robots_allowed, throttle
from deep_agent.utils.retry import http_retry

logger = get_logger("tasks.scraping")

# Tags that never carry meaningful article content.
_STRIP_TAGS = ("script", "style", "nav", "header", "footer", "aside", "noscript")
_MAX_CONTENT_CHARS = 20_000


@http_retry(max_attempts=3)
def _fetch(url: str, timeout: int, user_agent: str) -> httpx.Response:
    response = httpx.get(
        url,
        headers={"User-Agent": user_agent},
        timeout=timeout,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response


def _extract_text(html: str) -> tuple[str, str]:
    """Return ``(title, cleaned_text)`` from raw HTML."""

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_STRIP_TAGS):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""
    text = soup.get_text(separator="\n", strip=True)
    # Collapse excessive blank lines.
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return title, "\n".join(lines)[:_MAX_CONTENT_CHARS]


@celery_app.task(name="deep_agent.scrape_url", bind=True)
def scrape_url(self, url: str, timeout: int | None = None) -> dict:
    """Fetch and clean a single URL.

    Returns a ``ScrapedDocument`` serialised to a dict so it is
    JSON-safe for the Celery result backend.
    """

    settings = get_settings()
    timeout = timeout or settings.scrape_timeout_seconds
    user_agent = settings.scrape_user_agent

    # Politeness: honour robots.txt, then rate-limit per domain.
    if settings.respect_robots and not robots_allowed(url, user_agent, timeout):
        logger.warning("Skipping %s — disallowed by robots.txt", url)
        return ScrapedDocument(
            url=url, success=False, error="disallowed by robots.txt"
        ).model_dump(mode="json")

    throttle(url, settings.scrape_delay_seconds)

    logger.info("Scraping %s", url)
    try:
        response = _fetch(url, timeout, user_agent)
        title, content = _extract_text(response.text)
        doc = ScrapedDocument(
            url=url,
            title=title,
            content=content,
            word_count=len(content.split()),
            success=True,
        )
        logger.info("Scraped %s (%d words)", url, doc.word_count)
    except Exception as exc:  # noqa: BLE001 - reported on the document
        logger.error("Failed to scrape %s: %s", url, exc)
        doc = ScrapedDocument(url=url, success=False, error=str(exc))

    return doc.model_dump(mode="json")
