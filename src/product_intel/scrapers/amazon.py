"""Amazon product-page scraper.

Two entry points share one HTML parser:

* :func:`parse_amazon` - pure function turning saved page HTML into the raw
  payload the ingestion agent expects. No network; fully unit-testable.
* :class:`AmazonScraper` - drives Playwright to fetch the product page (and
  paginate the dedicated review pages) live, then parses with the same code.

Amazon actively blocks headless traffic (captcha / "Robot Check") and gates many
reviews behind login. :func:`is_blocked` detects the interstitial and the
scraper raises a clear, actionable error rather than returning garbage. When live
scraping is blocked, save the page from your own browser and use
``--html-file``.

Requires the ``scraping`` extra: ``pip install 'product-intel[scraping]'`` and
``playwright install chromium``. ``beautifulsoup4`` is imported lazily.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

_ASIN_RE = re.compile(r"/(?:dp|gp/product|product-reviews|gp/aw/d)/([A-Z0-9]{10})")
_RATING_RE = re.compile(r"([0-5](?:\.\d)?)\s+out of 5")
_BLOCK_MARKERS = (
    "Robot Check",
    "Enter the characters you see below",
    "To discuss automated access to Amazon data",
    "api-services-support@amazon.com",
    "Type the characters you see in this image",
)

_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


# --------------------------------------------------------------------------- #
# URL helpers
# --------------------------------------------------------------------------- #
def extract_asin(url: str) -> Optional[str]:
    """Pull the 10-char ASIN out of an Amazon product / review URL."""

    m = _ASIN_RE.search(url or "")
    return m.group(1) if m else None


def is_amazon_url(url: str) -> bool:
    host = urlparse(url or "").netloc.lower()
    return "amazon." in host or host.endswith("amazon.com")


def reviews_url(url: str, asin: str, page: int) -> str:
    parsed = urlparse(url)
    base = f"{parsed.scheme or 'https'}://{parsed.netloc}"
    return (
        f"{base}/product-reviews/{asin}/"
        f"?pageNumber={page}&reviewerType=all_reviews&sortBy=recent"
    )


# --------------------------------------------------------------------------- #
# Detection
# --------------------------------------------------------------------------- #
def is_blocked(html: str) -> bool:
    """True if the HTML is an anti-bot / captcha interstitial, not a real page."""

    if not html:
        return True
    return any(marker in html for marker in _BLOCK_MARKERS)


# --------------------------------------------------------------------------- #
# Parsing (pure)
# --------------------------------------------------------------------------- #
def _text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() if node else ""


def parse_product_metadata(soup, source_url: str = "") -> Dict[str, Any]:
    title = _text(soup.select_one("#productTitle"))

    brand = ""
    byline = soup.select_one("#bylineInfo")
    if byline:
        brand = re.sub(r"^(Visit the|Brand:)\s*", "", _text(byline))
        brand = re.sub(r"\s*Store$", "", brand).strip()
    if not brand:
        # product details table often has a "Manufacturer" / "Brand" row
        for row in soup.select("tr, .a-row"):
            label = _text(row.select_one("th, .a-span3, .a-text-bold"))
            if label.lower() in ("brand", "manufacturer"):
                brand = _text(row.select_one("td, .a-span9"))
                break

    price = None
    price_node = soup.select_one(
        "#corePrice_feature_div .a-offscreen, .a-price .a-offscreen, #priceblock_ourprice"
    )
    if price_node:
        m = re.search(r"[\d,]+(?:\.\d+)?", _text(price_node))
        if m:
            try:
                price = float(m.group(0).replace(",", ""))
            except ValueError:
                price = None

    features: List[str] = []
    for li in soup.select("#feature-bullets ul li span.a-list-item"):
        t = _text(li)
        if t and "See more product details" not in t:
            features.append(t)

    asin = extract_asin(source_url) or ""
    if not asin:
        asin_node = soup.select_one("[data-asin]")
        if asin_node and asin_node.get("data-asin"):
            asin = asin_node["data-asin"]

    return {
        "product_id": asin or (title[:24] or "AMZN-UNKNOWN"),
        "name": title,
        "manufacturer": brand,
        "price": price,
        "currency": "USD",
        "advertised_features": features,
        "source_url": source_url,
        "asin": asin,
    }


def parse_reviews(soup) -> List[Dict[str, Any]]:
    reviews: List[Dict[str, Any]] = []
    for block in soup.select('[data-hook="review"]'):
        rid = block.get("id") or None

        rating = None
        rating_node = block.select_one(
            '[data-hook="review-star-rating"] .a-icon-alt, '
            '[data-hook="cmps-review-star-rating"] .a-icon-alt, '
            'i[data-hook="review-star-rating"]'
        )
        if rating_node:
            m = _RATING_RE.search(_text(rating_node))
            if m:
                rating = float(m.group(1))

        title_node = block.select_one('[data-hook="review-title"]')
        # the visible title is usually the last span inside the title node
        title = ""
        if title_node:
            spans = title_node.select("span")
            title = _text(spans[-1]) if spans else _text(title_node)
            # strip a leading "5.0 out of 5 stars" that sometimes bleeds in
            title = _RATING_RE.sub("", title).strip(" .")

        body = _text(block.select_one('[data-hook="review-body"] span')) or _text(
            block.select_one('[data-hook="review-body"]')
        )

        date_raw = _text(block.select_one('[data-hook="review-date"]'))
        verified = bool(block.select_one('[data-hook="avp-badge"]'))

        if not body and not title:
            continue
        reviews.append(
            {
                "review_id": rid,
                "rating": rating,
                "title": title,
                "body": body,
                "date": date_raw,
                "verified": verified,
            }
        )
    return reviews


def parse_amazon(html: str, source_url: str = "") -> Dict[str, Any]:
    """Parse a saved Amazon product page into the ingestion payload.

    Raises ``RuntimeError`` if the HTML is an anti-bot interstitial.
    """

    if is_blocked(html):
        raise RuntimeError(
            "Amazon returned an anti-bot / captcha page, not product content. "
            "Save the page from your own logged-in browser and pass it with "
            "--html-file instead."
        )
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    return {
        "metadata": parse_product_metadata(soup, source_url),
        "reviews": parse_reviews(soup),
    }


# --------------------------------------------------------------------------- #
# Live scraper
# --------------------------------------------------------------------------- #
class AmazonScraper:
    """Fetch an Amazon product + its reviews live via Playwright."""

    def __init__(
        self,
        max_reviews: int = 100,
        headless: bool = True,
        page_pause: float = 1.5,
        user_agent: str = _DEFAULT_UA,
    ):
        try:
            import playwright  # noqa: F401
            import bs4  # noqa: F401
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError(
                "Live Amazon scraping needs: pip install 'product-intel[scraping]' "
                "and `playwright install chromium`."
            ) from exc
        self.max_reviews = max_reviews
        self.headless = headless
        self.page_pause = page_pause
        self.user_agent = user_agent

    def fetch(self, url: str) -> Dict[str, Any]:  # pragma: no cover - needs network
        if not is_amazon_url(url):
            raise ValueError(f"Not an Amazon URL: {url!r}")
        asin = extract_asin(url)

        from bs4 import BeautifulSoup
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless)
            context = browser.new_context(user_agent=self.user_agent, locale="en-US")
            page = context.new_page()

            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            html = page.content()
            if is_blocked(html):
                browser.close()
                raise RuntimeError(
                    "Amazon served an anti-bot / captcha page. Retry with "
                    "--no-headless, or save the page from your browser and use "
                    "--html-file."
                )
            soup = BeautifulSoup(html, "html.parser")
            metadata = parse_product_metadata(soup, url)
            reviews = parse_reviews(soup)
            asin = asin or metadata.get("asin")

            # Paginate the dedicated review pages for more than the ~8 on-page ones.
            if asin:
                page_num = 1
                max_pages = min(20, (self.max_reviews // 10) + 2)
                while len(reviews) < self.max_reviews and page_num <= max_pages:
                    rurl = reviews_url(url, asin, page_num)
                    try:
                        page.goto(rurl, wait_until="domcontentloaded", timeout=45000)
                        rhtml = page.content()
                    except Exception:
                        break
                    if is_blocked(rhtml):
                        break  # login/captcha wall - keep what we have
                    batch = parse_reviews(BeautifulSoup(rhtml, "html.parser"))
                    if not batch:
                        break
                    reviews.extend(batch)
                    page_num += 1
                    time.sleep(self.page_pause)

            browser.close()

        return {"metadata": metadata, "reviews": reviews[: self.max_reviews]}
