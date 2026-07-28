"""Source deduplication.

Two layers:
  1. URL canonicalization — strip tracking params, fragments, trailing slashes,
     and normalize scheme/host so `http://a.com/x?utm=1#h` == `https://a.com/x`.
  2. Near-duplicate detection — collapse sources whose titles are highly similar
     (same story republished across mirrors) using token Jaccard similarity.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models.schemas import Source

_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "ref", "ref_src", "igshid", "spm")
_WORD_RE = re.compile(r"[a-z0-9]+")


def canonical_url(url: str) -> str:
    """Return a canonical form of `url` suitable for equality comparison."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    scheme = "https" if parts.scheme in ("http", "https", "") else parts.scheme
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if not any(k.lower().startswith(p) for p in _TRACKING_PREFIXES)
    ]
    query = urlencode(sorted(query_pairs))
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, host, path, query, ""))


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def title_similarity(a: str, b: str) -> float:
    """Jaccard similarity over title tokens, in [0, 1]."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def deduplicate(
    sources: list[Source], *, title_threshold: float = 0.85
) -> list[Source]:
    """Collapse duplicate sources, keeping the first-seen (highest priority) copy.

    The caller is expected to pass sources ordered by preference (e.g. credibility
    desc), so the survivor of each duplicate group is the best one.
    """
    seen_urls: dict[str, Source] = {}
    kept: list[Source] = []

    for src in sources:
        cu = canonical_url(src.url)
        if cu and cu in seen_urls:
            continue

        # near-duplicate title check against already-kept sources
        is_near_dup = any(
            title_similarity(src.title, other.title) >= title_threshold
            for other in kept
            if src.title and other.title
        )
        if is_near_dup:
            continue

        if cu:
            seen_urls[cu] = src
        kept.append(src)

    return kept
