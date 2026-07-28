"""Heuristic source-credibility scoring.

Produces a score in [0, 1] used to (a) rank sources for reading, (b) break
dedup ties, and (c) annotate citations so the report can weight claims. This is
deliberately transparent and cheap — no LLM call. It combines:

  - Domain tier (peer-reviewed / gov / established press / reference / blog / unknown)
  - TLD signal (.gov / .edu / .org lean credible)
  - Backend signal (arxiv → academic; neural search slightly favored)
  - Recency (a published date within a few years nudges up)
  - Content depth (a source we actually read full text for scores higher)

The weights are intentionally conservative; the goal is sane ordering, not a
precise truth oracle.
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlsplit

# Curated domain tiers. Extend freely — unknown domains fall to the neutral base.
_TIER_SCORES: dict[str, float] = {
    "peer_reviewed": 0.95,
    "government": 0.9,
    "reference": 0.85,
    "established_press": 0.8,
    "industry_analyst": 0.82,
    "company_primary": 0.7,
    "blog_or_ugc": 0.4,
    "unknown": 0.5,
}

_DOMAIN_TIERS: dict[str, str] = {
    # peer-reviewed / academic
    "arxiv.org": "peer_reviewed",
    "nature.com": "peer_reviewed",
    "science.org": "peer_reviewed",
    "ncbi.nlm.nih.gov": "peer_reviewed",
    "ssrn.com": "peer_reviewed",
    # government / official statistics
    "sec.gov": "government",
    "bls.gov": "government",
    "census.gov": "government",
    "europa.eu": "government",
    "imf.org": "government",
    "worldbank.org": "government",
    # reference
    "wikipedia.org": "reference",
    "britannica.com": "reference",
    # established press
    "reuters.com": "established_press",
    "bloomberg.com": "established_press",
    "wsj.com": "established_press",
    "ft.com": "established_press",
    "economist.com": "established_press",
    "nytimes.com": "established_press",
    # industry analysts
    "gartner.com": "industry_analyst",
    "forrester.com": "industry_analyst",
    "mckinsey.com": "industry_analyst",
    "cbinsights.com": "industry_analyst",
    # user-generated / lower signal
    "medium.com": "blog_or_ugc",
    "substack.com": "blog_or_ugc",
    "reddit.com": "blog_or_ugc",
    "quora.com": "blog_or_ugc",
}

_UGC_TLDS = {"blogspot.com", "wordpress.com", "tumblr.com"}


def extract_domain(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _registrable(domain: str) -> str:
    """Best-effort registrable domain (last two labels). Not PSL-accurate, but fine here."""
    labels = domain.split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else domain


def classify_domain(domain: str) -> str:
    if domain in _DOMAIN_TIERS:
        return _DOMAIN_TIERS[domain]
    reg = _registrable(domain)
    if reg in _DOMAIN_TIERS:
        return _DOMAIN_TIERS[reg]
    if reg in _UGC_TLDS:
        return "blog_or_ugc"
    if domain.endswith(".gov"):
        return "government"
    if domain.endswith(".edu"):
        return "peer_reviewed"
    return "unknown"


def _recency_bonus(published: str | None) -> float:
    if not published:
        return 0.0
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y"):
        try:
            dt = datetime.strptime(published[: len(fmt) + 6], fmt)
            break
        except ValueError:
            continue
    else:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    age_days = (datetime.now(UTC) - dt).days
    if age_days < 0:
        return 0.0
    if age_days <= 365:
        return 0.06
    if age_days <= 365 * 3:
        return 0.03
    if age_days > 365 * 10:
        return -0.05  # stale
    return 0.0


def score_source(
    *,
    url: str,
    backend: str = "unknown",
    published: str | None = None,
    has_full_content: bool = False,
) -> float:
    """Return a credibility score in [0, 1]."""
    domain = extract_domain(url)
    tier = classify_domain(domain)
    base = _TIER_SCORES[tier]

    # Academic backend implies academic provenance even if domain is unlisted.
    if backend == "arxiv" and tier == "unknown":
        base = _TIER_SCORES["peer_reviewed"] - 0.1

    score = base
    score += _recency_bonus(published)
    if has_full_content:
        score += 0.03  # we could actually verify the claim against text

    return max(0.0, min(1.0, round(score, 4)))
