"""Country summary tool.

Given a country name, returns a concise factual summary (capital, region,
population, area, currencies, languages, ...) using the free, key-less REST
Countries API (https://restcountries.com).
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base import Tool
from .http import get_json

_API = "https://restcountries.com/v3.1/name/{name}"


def _fmt_number(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _pick_best(matches: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """Prefer an exact common/official name match over a fuzzy one."""
    q = query.strip().lower()
    for country in matches:
        names = country.get("name", {})
        common = (names.get("common") or "").lower()
        official = (names.get("official") or "").lower()
        if q in (common, official):
            return country
    return matches[0]


def _summarise_country(name: str) -> str:
    data = get_json(_API.format(name=name))
    if not isinstance(data, list) or not data:
        raise ValueError(f"No country found matching {name!r}.")

    c = _pick_best(data, name)
    names = c.get("name", {})
    common = names.get("common", name)
    official = names.get("official", common)

    capital = ", ".join(c.get("capital", []) or ["n/a"])
    region = c.get("region", "n/a")
    subregion = c.get("subregion", "")
    population = _fmt_number(c.get("population", "n/a"))
    area = _fmt_number(c.get("area", "n/a"))

    currencies = c.get("currencies", {}) or {}
    currency_str = ", ".join(
        f"{info.get('name', code)} ({info.get('symbol', '')}, {code})".strip()
        for code, info in currencies.items()
    ) or "n/a"

    languages = ", ".join((c.get("languages", {}) or {}).values()) or "n/a"
    timezones = ", ".join(c.get("timezones", []) or ["n/a"])
    borders = ", ".join(c.get("borders", []) or []) or "none"
    flag = c.get("flag", "")

    region_line = f"{region}" + (f" / {subregion}" if subregion else "")

    return (
        f"{flag} {common} ({official})\n"
        f"- Capital: {capital}\n"
        f"- Region: {region_line}\n"
        f"- Population: {population}\n"
        f"- Area: {area} km^2\n"
        f"- Currencies: {currency_str}\n"
        f"- Languages: {languages}\n"
        f"- Timezones: {timezones}\n"
        f"- Bordering countries (ISO codes): {borders}"
    )


COUNTRY_TOOL = Tool(
    name="country_summary",
    description=(
        "Get a concise factual summary of a country (capital, region, "
        "population, area, currencies, languages, timezones and neighbours). "
        "Pass the country name, e.g. 'France' or 'United Kingdom'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name of the country to summarise.",
            }
        },
        "required": ["name"],
    },
    handler=_summarise_country,
)

TOOLS = [COUNTRY_TOOL]
