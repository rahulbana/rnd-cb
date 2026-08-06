"""Festival date lookup.

Strategy:
  1. If a Calendarific API key is configured, query it (most accurate,
     handles lunar/movable festivals across many countries).
  2. Otherwise fall back to the LLM's knowledge, clearly flagged as an
     estimate that should be verified.
"""
from __future__ import annotations

from ..config import config
from ..agent.client import LLMUnavailable, complete
from .base import Tool, err, http_get_json, ok

CALENDARIFIC_URL = "https://calendarific.com/api/v2/holidays"


def _via_calendarific(festival: str, year: int, country: str) -> dict | None:
    try:
        data = http_get_json(
            CALENDARIFIC_URL,
            params={
                "api_key": config.CALENDARIFIC_API_KEY,
                "country": country,
                "year": year,
            },
        )
    except Exception:
        return None
    holidays = (data.get("response", {}) or {}).get("holidays", []) or []
    fl = festival.lower()
    for h in holidays:
        if fl in (h.get("name", "") or "").lower():
            d = h.get("date", {}).get("iso")
            return ok({
                "festival": h.get("name"),
                "year": year,
                "country": country,
                "date": d,
                "description": h.get("description"),
                "source": "calendarific",
            })
    return None


def _via_llm(festival: str, year: int, country: str) -> dict:
    try:
        result = complete(
            system="You are a calendar expert. Given a festival, a year and a "
                   "country, state the calendar date(s) it is/was celebrated. "
                   "Answer in one short sentence with the exact date. If uncertain, "
                   "say so.",
            user=f"When is {festival} celebrated in {country} in {year}?",
            temperature=0.0,
            max_tokens=200,
        )
    except LLMUnavailable as exc:
        return err(str(exc) + " (No Calendarific key set, so LLM fallback was needed.)")
    return ok({
        "festival": festival,
        "year": year,
        "country": country,
        "answer": result,
        "source": "llm-estimate",
        "note": "Estimated from model knowledge; verify for exact dates. Set "
                "CALENDARIFIC_API_KEY for authoritative data.",
    })


def get_festival_date(festival: str, year: int, country: str = "IN") -> dict:
    """Find the date a festival is celebrated in a given year and country."""
    if config.CALENDARIFIC_API_KEY:
        result = _via_calendarific(festival, year, country)
        if result:
            return result
    return _via_llm(festival, year, country)


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="get_festival_date",
            description="Find the date a festival is/was celebrated in a given year "
                        "and country (e.g. when was Holi celebrated in 1989).",
            category="Calendar",
            parameters={
                "type": "object",
                "properties": {
                    "festival": {"type": "string", "description": "Festival name, e.g. 'Holi'."},
                    "year": {"type": "integer", "description": "4-digit year."},
                    "country": {"type": "string", "description": "2-letter country code, default 'IN'."},
                },
                "required": ["festival", "year"],
            },
            func=get_festival_date,
        )
    ]
