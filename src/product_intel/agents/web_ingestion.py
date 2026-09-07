"""Agent 1 - Web Ingestion & Normalization.

Harvests product metadata + reviews from the target page, cleans noise,
normalizes dates, and validates everything into the :class:`IngestedProduct`
schema.

Scraping is pluggable behind the :class:`Scraper` protocol:

* :class:`FixtureScraper` (default) loads a saved JSON payload - deterministic,
  offline, used by tests and the sample run.
* :class:`PlaywrightScraper` performs real headless-browser extraction. It is
  imported lazily so ``playwright``/``bs4`` stay optional extras.

Both return the same raw ``dict``; normalization is identical regardless of source.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from ..schemas import IngestedProduct, ProductMetadata, Review

_WHITESPACE_RE = re.compile(r"\s+")
_DATE_FORMATS = (
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y",
    "%d %B %Y", "%d %b %Y", "%Y/%m/%d",
)


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", str(text)).strip()


def _normalize_date(raw: Optional[str]) -> Optional[str]:
    """Best-effort normalization of a review date to ISO-8601 (YYYY-MM-DD)."""

    if not raw:
        return None
    raw = str(raw).strip()
    # Strip common prefixes like "Reviewed in the US on 12 March 2023"
    m = re.search(r"on\s+(.*)$", raw)
    candidate = m.group(1).strip() if m else raw
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(candidate, fmt).date().isoformat()
        except ValueError:
            continue
    # already ISO-ish?
    if re.match(r"^\d{4}-\d{2}-\d{2}", candidate):
        return candidate[:10]
    return None


def _coerce_rating(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"([0-5](?:\.\d)?)", str(value))
    return float(m.group(1)) if m else 0.0


class Scraper(Protocol):
    def fetch(self, url: str) -> Dict[str, Any]:  # pragma: no cover - protocol
        ...


class FixtureScraper:
    """Loads a raw product payload from a JSON file or in-memory dict."""

    def __init__(self, payload: Optional[Dict[str, Any]] = None, path: Optional[str] = None):
        self._payload = payload
        self._path = path

    def fetch(self, url: str) -> Dict[str, Any]:
        if self._payload is not None:
            return self._payload
        if self._path is not None:
            with open(self._path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        raise ValueError("FixtureScraper needs either a payload or a path")


class PlaywrightScraper:  # pragma: no cover - requires optional extra + network
    """Real headless-browser scraper (opt-in).

    Requires ``pip install 'product-intel[scraping]'``. This is a minimal
    reference implementation of the DOM-extraction contract from the plan; site
    specific selectors would be supplied per marketplace.
    """

    def __init__(self, selectors: Optional[Dict[str, str]] = None, headless: bool = True):
        try:
            import playwright  # noqa: F401
            import bs4  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Live scraping needs: pip install 'product-intel[scraping]' "
                "and `playwright install chromium`."
            ) from exc
        self.selectors = selectors or {}
        self.headless = headless

    def fetch(self, url: str) -> Dict[str, Any]:
        from bs4 import BeautifulSoup
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, "html.parser")
        # NOTE: selector wiring is site-specific; left as a documented hook.
        title_sel = self.selectors.get("title", "h1")
        title_el = soup.select_one(title_sel)
        return {
            "metadata": {
                "product_id": url,
                "name": title_el.get_text(strip=True) if title_el else "",
                "source_url": url,
                "advertised_features": [],
            },
            "reviews": [],
        }


class WebIngestionAgent:
    """Agent 1: turn a URL (or fixture) into a validated :class:`IngestedProduct`."""

    def __init__(self, scraper: Optional[Scraper] = None):
        self.scraper = scraper or FixtureScraper()

    def run(self, url: str = "") -> IngestedProduct:
        raw = self.scraper.fetch(url)
        return self.normalize(raw)

    # -- normalization / validation ---------------------------------------- #
    def normalize(self, raw: Dict[str, Any]) -> IngestedProduct:
        meta_raw = raw.get("metadata") or raw.get("product") or {}
        metadata = ProductMetadata(
            product_id=str(meta_raw.get("product_id") or meta_raw.get("id") or "UNKNOWN"),
            name=_clean_text(meta_raw.get("name") or meta_raw.get("title")),
            manufacturer=_clean_text(meta_raw.get("manufacturer") or meta_raw.get("brand")),
            price=meta_raw.get("price"),
            currency=meta_raw.get("currency", "USD"),
            advertised_features=[
                _clean_text(f) for f in (meta_raw.get("advertised_features") or []) if _clean_text(f)
            ],
            source_url=_clean_text(meta_raw.get("source_url") or url_from(raw)),
        )
        if not metadata.name:
            raise ValueError("Ingestion failed: product name is required")

        reviews: List[Review] = []
        seen_bodies: set[str] = set()
        for i, r in enumerate(raw.get("reviews") or []):
            body = _clean_text(r.get("body") or r.get("text") or r.get("content"))
            if not body:
                continue
            dedup_key = body.lower()
            if dedup_key in seen_bodies:
                continue  # drop exact-duplicate scrape artifacts
            seen_bodies.add(dedup_key)
            reviews.append(
                Review(
                    review_id=str(r.get("review_id") or r.get("id") or f"R{i+1:04d}"),
                    rating=_coerce_rating(r.get("rating") or r.get("stars")),
                    title=_clean_text(r.get("title")),
                    body=body,
                    timestamp=_normalize_date(r.get("timestamp") or r.get("date")),
                    verified_purchase=bool(r.get("verified_purchase") or r.get("verified")),
                )
            )
        return IngestedProduct(metadata=metadata, reviews=reviews)


def url_from(raw: Dict[str, Any]) -> str:
    meta = raw.get("metadata") or raw.get("product") or {}
    return meta.get("source_url", "")
