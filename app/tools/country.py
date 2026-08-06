"""Country summary + current time in a country.

Structured facts come from REST Countries (free, no key). A short prose
summary (which typically mentions the head of state/government) comes from
the Wikipedia REST summary endpoint (free, no key).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .base import Tool, err, http_get_json, ok

REST_COUNTRIES_URL = "https://restcountries.com/v3.1/name/{name}"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"


def _wiki_summary(title: str) -> str | None:
    try:
        data = http_get_json(WIKI_SUMMARY_URL.format(title=title.replace(" ", "_")))
        return data.get("extract")
    except Exception:
        return None


def _best_match(results: list[dict], name: str) -> dict:
    """Prefer an exact common/official name match over a partial one."""
    name_l = name.strip().lower()
    for r in results:
        names = r.get("name", {})
        common = (names.get("common") or "").lower()
        official = (names.get("official") or "").lower()
        if name_l in (common, official):
            return r
    return results[0]


def get_country_summary(country: str) -> dict:
    """Return a rich summary of a country: capital, population, currency, etc."""
    try:
        results = http_get_json(REST_COUNTRIES_URL.format(name=country))
    except Exception:
        return err(f"Could not find country '{country}'.")
    if not results:
        return err(f"Could not find country '{country}'.")

    c = _best_match(results, country)
    names = c.get("name", {})
    common = names.get("common", country)
    currencies = c.get("currencies", {})
    currency_list = [
        f"{v.get('name')} ({k}, {v.get('symbol', '')})".strip()
        for k, v in currencies.items()
    ]
    languages = list((c.get("languages") or {}).values())

    summary = {
        "name": common,
        "official_name": names.get("official"),
        "capital": ", ".join(c.get("capital", []) or []),
        "region": c.get("region"),
        "subregion": c.get("subregion"),
        "population": c.get("population"),
        "area_km2": c.get("area"),
        "currencies": currency_list,
        "languages": languages,
        "timezones": c.get("timezones", []),
        "calling_code": "".join([
            (c.get("idd", {}).get("root") or ""),
            *(c.get("idd", {}).get("suffixes") or [])[:1],
        ]),
        "flag": c.get("flag"),
        "maps": (c.get("maps") or {}).get("googleMaps"),
    }
    # Head of state/government usually appears in the Wikipedia lead paragraph.
    overview = _wiki_summary(common)
    if overview:
        summary["overview"] = overview
    return ok(summary)


def _parse_utc_offset(tz: str) -> timedelta:
    """Parse an offset string like 'UTC+05:30' or 'UTC-04:00' into a timedelta."""
    tz = tz.replace("UTC", "").strip()
    if not tz or tz in ("+00:00", "±00:00"):
        return timedelta(0)
    sign = 1
    if tz[0] in "+-±":
        sign = -1 if tz[0] == "-" else 1
        tz = tz[1:]
    parts = tz.split(":")
    hours = int(parts[0]) if parts[0] else 0
    minutes = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    return sign * timedelta(hours=hours, minutes=minutes)


def get_time_in_country(country: str) -> dict:
    """Return the current local time(s) for a country based on its timezone(s)."""
    try:
        results = http_get_json(REST_COUNTRIES_URL.format(name=country))
    except Exception:
        return err(f"Could not find country '{country}'.")
    if not results:
        return err(f"Could not find country '{country}'.")

    c = _best_match(results, country)
    tzs = c.get("timezones", []) or []
    if not tzs:
        return err(f"No timezone information for '{country}'.")

    now_utc = datetime.now(timezone.utc)
    times = []
    for tz in tzs:
        local = now_utc + _parse_utc_offset(tz)
        times.append({
            "utc_offset": tz,
            "local_time": local.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return ok({
        "country": c.get("name", {}).get("common", country),
        "times": times,
    })


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="get_country_summary",
            description="Get a summary of a country by name: capital, population, "
                        "region, currencies, languages, timezones and a short "
                        "overview (which often names the head of state/government).",
            category="Reference",
            parameters={
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Country name, e.g. 'India'."},
                },
                "required": ["country"],
            },
            func=get_country_summary,
        ),
        Tool(
            name="get_time_in_country",
            description="Get the current local time in a country, by country name.",
            category="Reference",
            parameters={
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Country name."},
                },
                "required": ["country"],
            },
            func=get_time_in_country,
        ),
    ]
