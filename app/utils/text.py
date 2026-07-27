"""Lightweight text-parsing helpers used by the heuristic planner."""

from __future__ import annotations

import re

# Words that scale a bare number, e.g. "500k" or "1.5 million".
_MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "m": 1_000_000,
    "mn": 1_000_000,
    "million": 1_000_000,
    "b": 1_000_000_000,
    "bn": 1_000_000_000,
    "billion": 1_000_000_000,
}


def parse_int_count(text: str) -> int | None:
    """Extract a record/row count from free text.

    Handles ``"500,000 records"``, ``"250k customers"``, ``"1.5 million rows"``.
    Returns the first plausible count found, or ``None``.
    """

    lowered = text.lower()

    # "1.5 million" / "500k" / "2 m" style.
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*(k|m|mn|bn|b|thousand|million|billion)\b", lowered
    )
    if m:
        value = float(m.group(1)) * _MULTIPLIERS[m.group(2)]
        return int(round(value))

    # Plain integers with optional thousands separators near a size keyword.
    for kw in ("records", "rows", "customers", "samples", "examples", "users"):
        m = re.search(r"([\d,]{2,})\s*" + kw, lowered)
        if m:
            return int(m.group(1).replace(",", ""))

    # Last resort: any standalone number with >=3 digits.
    m = re.search(r"\b(\d{3,}(?:,\d{3})*)\b", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def parse_percentage(text: str, keywords: list[str]) -> float | None:
    """Find a percentage tied to one of ``keywords``.

    ``"2% fraud rate"`` with ``keywords=["fraud"]`` -> ``0.02``. Also matches the
    percentage appearing just before the keyword (``"12% churn"``).
    """

    lowered = text.lower()
    for kw in keywords:
        # "<pct>% ... <kw>" or "<kw> ... <pct>%"
        for pattern in (
            r"(\d+(?:\.\d+)?)\s*%[^.]*?" + re.escape(kw),
            re.escape(kw) + r"[^.]*?(\d+(?:\.\d+)?)\s*%",
        ):
            m = re.search(pattern, lowered)
            if m:
                return float(m.group(1)) / 100.0
    return None


def parse_feature_counts(text: str) -> tuple[int | None, int | None]:
    """Return ``(numeric, categorical)`` feature counts if stated."""

    lowered = text.lower()
    numeric = None
    categorical = None
    m = re.search(r"(\d+)\s*(?:numer|numeric|continuous|float|int)", lowered)
    if m:
        numeric = int(m.group(1))
    m = re.search(r"(\d+)\s*categor", lowered)
    if m:
        categorical = int(m.group(1))
    # Generic "N features" only sets the numeric bucket if nothing else did.
    if numeric is None and categorical is None:
        m = re.search(r"(\d+)\s*(?:engineered\s+)?features?", lowered)
        if m:
            numeric = int(m.group(1))
    return numeric, categorical


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "dataset"
