"""Public holidays for a country/year (Nager.Date API, free, no key)."""
from __future__ import annotations

from datetime import date

from .base import Tool, err, http_get_json, ok

HOLIDAYS_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/{code}"
COUNTRIES_URL = "https://date.nager.at/api/v3/AvailableCountries"

_code_cache: dict[str, str] | None = None


def _country_code(country: str) -> str | None:
    """Map a country name (or 2-letter code) to a Nager ISO-3166 alpha-2 code."""
    global _code_cache
    country = country.strip()
    if len(country) == 2 and country.isalpha():
        return country.upper()
    if _code_cache is None:
        try:
            data = http_get_json(COUNTRIES_URL)
            _code_cache = {c["name"].lower(): c["countryCode"] for c in data}
        except Exception:
            _code_cache = {}
    # exact then partial match
    cl = country.lower()
    if cl in _code_cache:
        return _code_cache[cl]
    for name, code in _code_cache.items():
        if cl in name:
            return code
    return None


def get_public_holidays(country: str, year: int | None = None) -> dict:
    """Return the list of public holidays for a country in a given year."""
    year = year or date.today().year
    code = _country_code(country)
    if not code:
        return err(f"Could not resolve country '{country}' to a country code.")
    try:
        data = http_get_json(HOLIDAYS_URL.format(year=year, code=code))
    except Exception:
        return err(f"No public holiday data for '{country}' ({code}) in {year}.")

    holidays = [
        {
            "date": h.get("date"),
            "name": h.get("name"),
            "local_name": h.get("localName"),
            "global": h.get("global"),
        }
        for h in data
    ]
    return ok({"country": country, "country_code": code, "year": year,
               "count": len(holidays), "holidays": holidays})


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="get_public_holidays",
            description="Get the list of public holidays in a country for a given "
                        "year (defaults to the current year).",
            category="Calendar",
            parameters={
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Country name or 2-letter code."},
                    "year": {"type": "integer", "description": "4-digit year. Optional."},
                },
                "required": ["country"],
            },
            func=get_public_holidays,
        )
    ]
