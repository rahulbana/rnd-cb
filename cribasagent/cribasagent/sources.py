"""News sources for the agent.

We rely on the public RSS feeds of major Indian English-language newspapers
and government wires. RSS is far more reliable and polite than scraping HTML,
gives clean timestamps for the 24-hour window, and avoids breaking every time
a site redesigns. Add or remove sources here without touching the rest of the
codebase.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewsSource:
    """A single RSS feed plus a human-friendly label."""

    name: str
    url: str
    # A coarse beat hint that helps the LLM weight relevance. Optional.
    section: str = "general"


# Curated for UPSC / general-knowledge value: national affairs, economy,
# polity, international relations, science, environment and official releases.
DEFAULT_SOURCES: tuple[NewsSource, ...] = (
    NewsSource("The Hindu - National", "https://www.thehindu.com/news/national/feeder/default.rss", "national"),
    NewsSource("The Hindu - Business", "https://www.thehindu.com/business/feeder/default.rss", "economy"),
    NewsSource("The Hindu - International", "https://www.thehindu.com/news/international/feeder/default.rss", "international"),
    NewsSource("The Hindu - Sci-Tech", "https://www.thehindu.com/sci-tech/feeder/default.rss", "science"),
    NewsSource("Indian Express - India", "https://indianexpress.com/section/india/feed/", "national"),
    NewsSource("Indian Express - Explained", "https://indianexpress.com/section/explained/feed/", "explained"),
    NewsSource("Indian Express - Business", "https://indianexpress.com/section/business/feed/", "economy"),
    NewsSource("Times of India - India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", "national"),
    NewsSource("Times of India - World", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "international"),
    NewsSource("Hindustan Times - India", "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "national"),
    NewsSource("LiveMint - Economy", "https://www.livemint.com/rss/economy", "economy"),
    NewsSource("PIB - Press Releases", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3", "government"),
    NewsSource("Down To Earth", "https://www.downtoearth.org.in/rss/news", "environment"),
)
