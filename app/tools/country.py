"""Country summary + current time in a country.

Structured facts come from REST Countries (free, no key). Because that service
is community-run and intermittently unavailable, failures are surfaced with the
real HTTP status and the summary falls back to a Wikipedia extract (which also
usually names the head of state/government) so the tool still returns useful
information instead of a bare error.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx

from .base import Tool, err, http_get, http_get_json, ok

REST_COUNTRIES_URL = "https://restcountries.com/v3.1/name/{name}"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

# Only request the fields we use: smaller/faster responses and it sidesteps
# deployments that reject unfiltered queries.
SUMMARY_FIELDS = ("name,capital,region,subregion,population,area,currencies,"
                  "languages,timezones,idd,flag,maps")
TIME_FIELDS = "name,timezones"


class CountryNotFound(Exception):
    """No country matched the given name (HTTP 404)."""


class CountryServiceError(Exception):
    """The country data service could not be reached or returned an error."""


def _wiki_summary(title: str) -> str | None:
    try:
        data = http_get_json(WIKI_SUMMARY_URL.format(title=quote(title.strip().replace(" ", "_"))))
        return data.get("extract")
    except Exception:
        return None


def _fetch_country_records(country: str, fields: str) -> list[dict]:
    """Fetch matching country records, raising typed errors on failure.

    Retries once without the ``fields`` filter if the service rejects it (some
    deployments respond 400 to filtered queries).
    """
    url = REST_COUNTRIES_URL.format(name=quote(country.strip()))

    def _request(params: dict | None) -> list[dict]:
        return http_get(url, params=params).json()

    try:
        return _request({"fields": fields})
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 400:
            # The fields filter may be unsupported; retry unfiltered.
            try:
                return _request(None)
            except httpx.HTTPStatusError as exc2:
                status = exc2.response.status_code
        if status == 404:
            raise CountryNotFound(country) from exc
        raise CountryServiceError(f"country data service returned HTTP {status}") from exc
    except httpx.HTTPError as exc:
        raise CountryServiceError(
            f"could not reach country data service ({type(exc).__name__})"
        ) from exc


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
        records = _fetch_country_records(country, SUMMARY_FIELDS)
    except CountryNotFound:
        return err(f"No country matched '{country}'. Check the spelling.")
    except CountryServiceError as exc:
        # Structured source is down — fall back to an encyclopedic summary so the
        # user still gets the capital, leaders, etc. from the prose extract.
        overview = _wiki_summary(country)
        if overview:
            return ok({
                "name": country.strip().title(),
                "overview": overview,
                "note": f"Structured country data was unavailable ({exc}); "
                        "showing an encyclopedic summary instead.",
            }, partial=True)
        return err(f"Country lookup failed: {exc}. Please try again shortly.")

    if not records:
        return err(f"No country matched '{country}'.")

    c = _best_match(records, country)
    names = c.get("name", {})
    common = names.get("common", country)
    currencies = c.get("currencies", {}) or {}
    currency_list = [
        f"{v.get('name')} ({k}, {v.get('symbol', '')})".strip()
        for k, v in currencies.items()
    ]
    languages = list((c.get("languages") or {}).values())
    idd = c.get("idd", {}) or {}

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
            (idd.get("root") or ""),
            *(idd.get("suffixes") or [])[:1],
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
        records = _fetch_country_records(country, TIME_FIELDS)
    except CountryNotFound:
        return err(f"No country matched '{country}'. Check the spelling.")
    except CountryServiceError as exc:
        return err(f"Could not look up '{country}': {exc}. Please try again shortly.")

    if not records:
        return err(f"No country matched '{country}'.")

    c = _best_match(records, country)
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
