"""Tests for the Amazon scraper's pure parsing layer (no network).

The parser needs beautifulsoup4 (the `scraping` extra); tests skip cleanly when
it is not installed.
"""

from pathlib import Path

import pytest

pytest.importorskip("bs4")

from product_intel import Orchestrator  # noqa: E402
from product_intel.agents.web_ingestion import FixtureScraper  # noqa: E402
from product_intel.scrapers.amazon import (  # noqa: E402
    extract_asin,
    is_amazon_url,
    is_blocked,
    parse_amazon,
    reviews_url,
)

SAMPLE_HTML = (Path(__file__).parent / "data" / "amazon_sample.html").read_text(encoding="utf-8")
PRODUCT_URL = "https://www.amazon.com/dp/B0ABCDE123"


# --- URL helpers ----------------------------------------------------------- #
@pytest.mark.parametrize("url,asin", [
    ("https://www.amazon.com/dp/B0ABCDE123", "B0ABCDE123"),
    ("https://www.amazon.com/gp/product/B0ABCDE123/ref=x", "B0ABCDE123"),
    ("https://amazon.in/Some-Title/dp/B0ABCDE123?th=1", "B0ABCDE123"),
    ("https://www.amazon.com/product-reviews/B0ABCDE123/", "B0ABCDE123"),
    ("https://www.amazon.com/", None),
])
def test_extract_asin(url, asin):
    assert extract_asin(url) == asin


def test_is_amazon_url():
    assert is_amazon_url("https://www.amazon.com/dp/B0ABCDE123")
    assert is_amazon_url("https://amazon.in/dp/B0ABCDE123")
    assert not is_amazon_url("https://www.flipkart.com/p/itm123")


def test_reviews_url_shape():
    u = reviews_url(PRODUCT_URL, "B0ABCDE123", 2)
    assert "/product-reviews/B0ABCDE123/" in u
    assert "pageNumber=2" in u


# --- block detection ------------------------------------------------------- #
def test_is_blocked_detects_captcha():
    assert is_blocked("<html><body>Robot Check ... Enter the characters you see below</body></html>")
    assert not is_blocked(SAMPLE_HTML)
    assert is_blocked("")


def test_parse_amazon_raises_on_block():
    with pytest.raises(RuntimeError):
        parse_amazon("<html>Type the characters you see in this image</html>")


# --- parsing --------------------------------------------------------------- #
def test_parse_metadata():
    payload = parse_amazon(SAMPLE_HTML, source_url=PRODUCT_URL)
    meta = payload["metadata"]
    assert meta["name"].startswith("AcousticPro Wireless ANC Headphones")
    assert meta["manufacturer"] == "AcousticPro"
    assert meta["price"] == 249.99
    assert meta["asin"] == "B0ABCDE123"
    assert meta["product_id"] == "B0ABCDE123"
    # feature bullets extracted, "See more product details" filtered out
    assert "Industry-leading Active Noise Cancellation" in meta["advertised_features"]
    assert all("See more product details" not in f for f in meta["advertised_features"])


def test_parse_reviews():
    payload = parse_amazon(SAMPLE_HTML, source_url=PRODUCT_URL)
    reviews = payload["reviews"]
    assert len(reviews) == 3
    first = reviews[0]
    assert first["rating"] == 5.0
    assert first["title"] == "Blocks the subway completely"
    assert "noise cancellation" in first["body"].lower()
    assert first["verified"] is True
    assert "March 5, 2024" in first["date"]
    # second review is unverified
    assert reviews[1]["verified"] is False
    assert reviews[1]["rating"] == 2.0


# --- integration: parsed payload flows through the whole pipeline ---------- #
def test_amazon_payload_runs_end_to_end():
    payload = parse_amazon(SAMPLE_HTML, source_url=PRODUCT_URL)
    report = Orchestrator(scraper=FixtureScraper(payload=payload)).run(url=PRODUCT_URL)
    d = report.to_dict()
    assert d["product_summary"]["product_id"] == "B0ABCDE123"
    assert d["product_summary"]["total_reviews_analyzed"] == 3
    # dates were normalized to ISO by the ingestion agent
    assert d["vnext_backlog"], "expected a backlog from the parsed Amazon reviews"
