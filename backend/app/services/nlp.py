"""Natural-language trip parsing (spec section 16).

Deterministic extraction of structured requirements from free text (duration,
travelers, budget, month, destinations, interests). This is fast, testable and
runs offline; the LLM can refine ambiguous cases but never silently overrides
what the user explicitly stated.
"""
from __future__ import annotations

import re
from datetime import date

from ..schemas.common import Money, TravelerType
from ..schemas.trip import TripRequest, UserPreferences
from ..tools.geocode import _GAZETTEER

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}

_CURRENCY_SYMBOLS = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
_CURRENCY_WORDS = {"inr": "INR", "rupee": "INR", "rupees": "INR", "lakh": "INR",
                   "usd": "USD", "dollar": "USD", "dollars": "USD",
                   "eur": "EUR", "euro": "EUR", "euros": "EUR",
                   "gbp": "GBP", "pound": "GBP", "pounds": "GBP", "yen": "JPY"}

_INTEREST_WORDS = ["food", "culture", "photography", "beach", "beaches", "nightlife",
                   "shopping", "history", "nature", "hiking", "adventure", "art",
                   "museums", "relaxation", "wildlife", "architecture"]

_DIETARY_WORDS = ["vegetarian", "vegan", "halal", "kosher", "gluten-free", "gluten free"]

_STOPWORDS = {"the", "a", "an", "my", "our", "me", "next", "this", "and", "for",
              "with", "in", "on", "from", "to", "us", "we", "some", "few"}


def _extract_after(lower: str, prep: str) -> str | None:
    """Return the place mentioned after ``prep`` (e.g. 'from delhi').

    Matches a known two-word gazetteer city first, then a single word, skipping
    connective stop-words and month names so 'from Delhi in October' -> 'Delhi'.
    """
    m = re.search(rf"\b{prep}\s+([a-z]+)(?:\s+([a-z]+))?", lower)
    if not m:
        return None
    first, second = m.group(1), m.group(2)
    if second:
        two = f"{first} {second}"
        if two in _GAZETTEER:
            return two.title()
    if first in _STOPWORDS or first in _MONTHS:
        return None
    return first.title()


def parse_trip_request(text: str) -> TripRequest:
    lower = f" {text.lower()} "
    req = TripRequest(notes=text.strip() or None)

    # Duration: "8 days", "10-day", "a week"
    m = re.search(r"(\d+)\s*[-\s]?day", lower)
    if m:
        req.duration_days = min(int(m.group(1)), 90)
    elif re.search(r"\bweekend\b", lower):
        req.duration_days = 3
    elif re.search(r"\bweeks?\b", lower):
        weeks = re.search(r"(\d+)\s*weeks?\b", lower)
        req.duration_days = (int(weeks.group(1)) if weeks else 1) * 7

    # Travelers
    if any(w in lower for w in (" family", " kids", " children")):
        req.traveler_type = TravelerType.FAMILY
        req.travelers = max(req.travelers, 3)
    elif any(w in lower for w in (" honeymoon", " wife", " husband", " partner", " couple", " two people")):
        req.traveler_type = TravelerType.COUPLE
        req.travelers = 2
    elif " business" in lower:
        req.traveler_type = TravelerType.BUSINESS
    people = re.search(r"(\d+)\s*(?:people|persons|travelers|travellers|adults)", lower)
    if people:
        req.travelers = min(int(people.group(1)), 30)

    # Budget
    budget = _parse_budget(text)
    if budget:
        req.budget = budget

    # Month -> a nominal start date this or next year
    for name, idx in _MONTHS.items():
        if name in lower:
            year = date.today().year if idx >= date.today().month else date.today().year + 1
            req.start_date = date(year, idx, 5)
            break

    # Origin: "from X" (single token, or a known two-word gazetteer city)
    origin_word = _extract_after(lower, "from")
    if origin_word:
        req.origin = origin_word

    # Destinations: prefer gazetteer hits, then "to X".
    origin_key = (req.origin or "").lower()
    dests: list[str] = []
    to_word = _extract_after(lower, "to")
    if to_word:
        dests.append(to_word)
    for name in _GAZETTEER:  # multi-word cities like "new york"
        if name in lower and name != origin_key:
            dests.append(name.title())
    # De-duplicate case-insensitively and drop the origin.
    seen: set[str] = set()
    req.destinations = [
        d for d in dests
        if d.lower() != origin_key and not (d.lower() in seen or seen.add(d.lower()))
    ]

    # Preferences
    prefs = UserPreferences(
        interests=[w for w in _INTEREST_WORDS if w in lower],
        dietary=[w for w in _DIETARY_WORDS if w in lower],
    )
    if " luxury" in lower or " premium" in lower:
        prefs.travel_style = prefs.travel_style.LUXURY
    elif " budget" in lower or " cheap" in lower or " backpack" in lower:
        prefs.travel_style = prefs.travel_style.BUDGET
    req.preferences = prefs

    return req


def _parse_budget(text: str) -> Money | None:
    lower = text.lower()
    currency = "USD"
    for sym, code in _CURRENCY_SYMBOLS.items():
        if sym in text:
            currency = code
            break
    else:
        for word, code in _CURRENCY_WORDS.items():
            if word in lower:
                currency = code
                break

    # "₹2,00,000", "2.5 lakh", "$2500", "2000 dollars"
    lakh = re.search(r"([\d.]+)\s*lakh", lower)
    if lakh:
        return Money(amount=float(lakh.group(1)) * 100_000, currency="INR")
    crore = re.search(r"([\d.]+)\s*crore", lower)
    if crore:
        return Money(amount=float(crore.group(1)) * 10_000_000, currency="INR")

    amounts = re.findall(r"[₹$€£¥]?\s?([\d][\d,]{2,})", text)
    if amounts:
        raw = amounts[0].replace(",", "")
        try:
            value = float(raw)
            if value >= 100:  # ignore small numbers like years/days
                return Money(amount=value, currency=currency)
        except ValueError:
            return None
    return None
