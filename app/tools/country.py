"""Country summary + current time in a country.

Reliability notes:
  - REST Countries (restcountries.com) is a community-run service that is
    frequently slow or unavailable. We therefore do NOT depend on it.
  - The country summary is built on Wikipedia (very reliable, and the only
    source here that actually names the head of state/government), with REST
    Countries used only as best-effort enrichment for structured fields.
  - The time lookup uses Open-Meteo geocoding (the same reliable service the
    weather tool uses) to resolve an IANA timezone, falling back to REST
    Countries only if geocoding fails.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from .base import Tool, err, http_get, http_get_json, ok
from .geo import geocode

REST_COUNTRIES_URL = "https://restcountries.com/v3.1/name/{name}"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

SUMMARY_FIELDS = ("name,capital,region,subregion,population,area,currencies,"
                  "languages,timezones,idd,flag,maps")
# Keep the flaky service from stalling the whole tool.
REST_TIMEOUT = 8.0


class CountryNotFound(Exception):
    """No country matched the given name (HTTP 404)."""


class CountryServiceError(Exception):
    """The REST Countries service could not be reached or returned an error."""


# --------------------------- data sources ---------------------------

def _wiki_summary(title: str) -> str | None:
    """Return the lead paragraph for a country from Wikipedia, or None."""
    try:
        data = http_get_json(
            WIKI_SUMMARY_URL.format(title=quote(title.strip().replace(" ", "_"))),
            timeout=12.0,
        )
        # Disambiguation / missing pages have no useful extract.
        if data.get("type") == "disambiguation":
            return None
        return data.get("extract") or None
    except Exception:
        return None


def _fetch_country_records(country: str, fields: str) -> list[dict]:
    """Fetch matching country records from REST Countries (best-effort).

    Raises CountryNotFound (404) or CountryServiceError (anything else) so the
    caller can decide whether to fall back.
    """
    url = REST_COUNTRIES_URL.format(name=quote(country.strip()))

    def _request(params: dict | None):
        return http_get(url, params=params, timeout=REST_TIMEOUT).json()

    try:
        data = _request({"fields": fields})
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 400:  # some deployments reject the fields filter
            try:
                data = _request(None)
            except httpx.HTTPStatusError as exc2:
                status = exc2.response.status_code
                if status == 404:
                    raise CountryNotFound(country) from exc2
                raise CountryServiceError(
                    f"restcountries.com returned HTTP {status}") from exc2
        elif status == 404:
            raise CountryNotFound(country) from exc
        else:
            raise CountryServiceError(
                f"restcountries.com returned HTTP {status}") from exc
    except httpx.HTTPError as exc:
        raise CountryServiceError(
            f"restcountries.com unreachable ({type(exc).__name__})") from exc

    return _validate_records(data, country)


def _validate_records(data, country: str) -> list[dict]:
    """Normalize a REST Countries response into a list of country dicts.

    The service sometimes returns an error object such as
    ``{"status": 404, "message": "Not Found"}`` with a 200 status code (so no
    HTTPStatusError is raised). Detect that and other non-list shapes instead
    of letting them flow through as if they were country records.
    """
    if isinstance(data, dict):
        if data.get("status") == 404 or "Not Found" in str(data.get("message", "")):
            raise CountryNotFound(country)
        raise CountryServiceError(
            f"restcountries.com error: {data.get('message') or data}")
    if not isinstance(data, list):
        raise CountryServiceError("unexpected response format from restcountries.com")
    records = [r for r in data if isinstance(r, dict)]
    if not records:
        raise CountryNotFound(country)
    return records


def _best_match(results: list[dict], name: str) -> dict:
    """Prefer an exact common/official name match over a partial one."""
    name_l = name.strip().lower()
    for r in results:
        if not isinstance(r, dict):
            continue
        names = r.get("name", {}) or {}
        common = (names.get("common") or "").lower()
        official = (names.get("official") or "").lower()
        if name_l in (common, official):
            return r
    return results[0]


def _extract_structured(c: dict) -> dict:
    """Pull the structured fields we expose out of a REST Countries record."""
    names = c.get("name", {})
    currencies = c.get("currencies", {}) or {}
    currency_list = [
        f"{v.get('name')} ({k}, {v.get('symbol', '')})".strip()
        for k, v in currencies.items()
    ]
    idd = c.get("idd", {}) or {}
    return {
        "name": names.get("common"),
        "official_name": names.get("official"),
        "capital": ", ".join(c.get("capital", []) or []),
        "region": c.get("region"),
        "subregion": c.get("subregion"),
        "population": c.get("population"),
        "area_km2": c.get("area"),
        "currencies": currency_list,
        "languages": list((c.get("languages") or {}).values()),
        "timezones": c.get("timezones", []),
        "calling_code": "".join([
            (idd.get("root") or ""),
            *(idd.get("suffixes") or [])[:1],
        ]),
        "flag": c.get("flag"),
        "maps": (c.get("maps") or {}).get("googleMaps"),
    }


# ------------------------------ tools -------------------------------

def get_country_summary(country: str) -> dict:
    """Return a summary of a country: capital, population, currency, leaders, etc.

    Succeeds as long as EITHER Wikipedia or REST Countries is reachable.
    """
    # 1) Reliable backbone: the Wikipedia lead paragraph (capital, leaders, …).
    overview = _wiki_summary(country)

    # 2) Best-effort structured enrichment from REST Countries.
    structured: dict | None = None
    struct_error: str | None = None
    try:
        records = _fetch_country_records(country, SUMMARY_FIELDS)
        if records:
            structured = _extract_structured(_best_match(records, country))
    except CountryNotFound:
        struct_error = "not_found"
    except CountryServiceError as exc:
        struct_error = str(exc)

    if structured:
        if overview:
            structured["overview"] = overview
        if not structured.get("name"):
            structured["name"] = country.strip().title()
        return ok(structured)

    # 3) No structured data — return the encyclopedic summary if we have it.
    if overview:
        note = "Detailed structured data was unavailable"
        if struct_error and struct_error != "not_found":
            note += f" ({struct_error})"
        note += "; showing an encyclopedic summary."
        return ok({
            "name": country.strip().title(),
            "overview": overview,
            "note": note,
        }, partial=True)

    # 4) Everything failed.
    if struct_error == "not_found":
        return err(f"No country matched '{country}'. Check the spelling.")
    return err(
        f"Could not retrieve information for '{country}'. Both Wikipedia and the "
        f"country data service ({struct_error or 'unreachable'}) were unavailable "
        "— check your internet connection and try again."
    )


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


def _time_via_geocoding(country: str) -> dict | None:
    """Resolve a representative local time using Open-Meteo geocoding + zoneinfo."""
    try:
        loc = geocode(country)
    except Exception:
        return None
    if not loc or not loc.get("timezone"):
        return None
    try:
        now = datetime.now(ZoneInfo(loc["timezone"]))
    except Exception:
        return None
    return {
        "country": loc.get("country") or country.strip().title(),
        "times": [{
            "timezone": loc["timezone"],
            "utc_offset": now.strftime("%z"),
            "local_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        }],
        "source": "open-meteo",
    }


def get_time_in_country(country: str) -> dict:
    """Return the current local time in a country, by country name."""
    # 1) Try REST Countries first (lists every timezone the country spans).
    try:
        records = _fetch_country_records(country, "name,timezones")
        c = _best_match(records, country)
        tzs = c.get("timezones", []) or []
        if tzs:
            now_utc = datetime.now(timezone.utc)
            times = [{
                "utc_offset": tz,
                "local_time": (now_utc + _parse_utc_offset(tz)).strftime("%Y-%m-%d %H:%M:%S"),
            } for tz in tzs]
            return ok({
                "country": c.get("name", {}).get("common", country),
                "times": times,
                "source": "restcountries",
            })
    except (CountryNotFound, CountryServiceError):
        pass  # fall through to the reliable geocoding path

    # 2) Reliable fallback: geocode the country (same service the weather tool uses).
    result = _time_via_geocoding(country)
    if result:
        return ok(result)

    return err(f"Could not determine the time for '{country}'. "
               "Check the spelling or your internet connection.")


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
