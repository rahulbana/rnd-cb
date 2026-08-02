"""World-time and timezone utilities built on the stdlib ``zoneinfo`` database.

These tools let the agent answer "what time is it in Tokyo?" and "what's the
offset between New York and London right now?" without any external service.
A small alias table maps common city / country names to IANA timezone keys so
users don't have to know that Tokyo is ``Asia/Tokyo``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, available_timezones

# Friendly aliases -> IANA timezone identifiers.
_ALIASES: dict[str, str] = {
    "utc": "UTC",
    "gmt": "UTC",
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "toronto": "America/Toronto",
    "mexico city": "America/Mexico_City",
    "sao paulo": "America/Sao_Paulo",
    "london": "Europe/London",
    "uk": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "madrid": "Europe/Madrid",
    "rome": "Europe/Rome",
    "amsterdam": "Europe/Amsterdam",
    "moscow": "Europe/Moscow",
    "dubai": "Asia/Dubai",
    "india": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "singapore": "Asia/Singapore",
    "hong kong": "Asia/Hong_Kong",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "tokyo": "Asia/Tokyo",
    "japan": "Asia/Tokyo",
    "seoul": "Asia/Seoul",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "auckland": "Pacific/Auckland",
}


class TimezoneError(ValueError):
    """Raised when a location cannot be resolved to a timezone."""


def _resolve_zone(location: str) -> ZoneInfo:
    token = location.strip()
    if not token:
        raise TimezoneError("A location or timezone name is required.")

    lowered = token.lower()
    if lowered in _ALIASES:
        return ZoneInfo(_ALIASES[lowered])

    # Accept an exact IANA key regardless of case, e.g. "asia/tokyo".
    for zone in available_timezones():
        if zone.lower() == lowered:
            return ZoneInfo(zone)

    # Fuzzy match on the city portion of any IANA key (e.g. "kolkata").
    needle = lowered.replace(" ", "_")
    matches = [z for z in available_timezones() if z.split("/")[-1].lower() == needle]
    if len(matches) == 1:
        return ZoneInfo(matches[0])

    raise TimezoneError(
        f"Could not resolve '{location}' to a timezone. Try an IANA name like "
        f"'Asia/Tokyo' or a major city such as 'Tokyo'."
    )


def _describe(zone: ZoneInfo, when: datetime) -> dict[str, Any]:
    local = when.astimezone(zone)
    offset = local.utcoffset()
    total_minutes = int(offset.total_seconds() // 60) if offset else 0
    sign = "+" if total_minutes >= 0 else "-"
    hh, mm = divmod(abs(total_minutes), 60)
    return {
        "timezone": str(zone),
        "iso8601": local.isoformat(),
        "date": local.strftime("%Y-%m-%d"),
        "time": local.strftime("%H:%M:%S"),
        "day_of_week": local.strftime("%A"),
        "abbreviation": local.tzname(),
        "utc_offset": f"{sign}{hh:02d}:{mm:02d}",
        "is_dst": bool(local.dst()),
    }


def current_time(location: str) -> dict[str, Any]:
    """Return the current wall-clock time for a city, country, or IANA zone."""
    zone = _resolve_zone(location)
    return _describe(zone, datetime.now(tz=ZoneInfo("UTC")))


def compare_timezones(location_a: str, location_b: str) -> dict[str, Any]:
    """Compare the current time in two locations and report the offset."""
    now = datetime.now(tz=ZoneInfo("UTC"))
    a = _describe(_resolve_zone(location_a), now)
    b = _describe(_resolve_zone(location_b), now)

    off_a = datetime.fromisoformat(a["iso8601"]).utcoffset()
    off_b = datetime.fromisoformat(b["iso8601"]).utcoffset()
    delta_minutes = int(((off_a or off_b) and (off_a - off_b).total_seconds() // 60) or 0)
    sign = "ahead" if delta_minutes >= 0 else "behind"
    hh, mm = divmod(abs(delta_minutes), 60)

    return {
        "location_a": a,
        "location_b": b,
        "difference": f"{location_a} is {hh}h {mm}m {sign} of {location_b}",
        "difference_minutes": delta_minutes,
    }


def convert_time(time_str: str, from_location: str, to_location: str) -> dict[str, Any]:
    """Convert a wall-clock ``HH:MM`` (24h) time from one zone to another (today)."""
    from_zone = _resolve_zone(from_location)
    to_zone = _resolve_zone(to_location)
    try:
        parsed = datetime.strptime(time_str.strip(), "%H:%M").time()
    except ValueError as exc:
        raise TimezoneError("time_str must be in 24-hour 'HH:MM' format, e.g. '14:30'.") from exc

    today = datetime.now(tz=from_zone).date()
    source_dt = datetime.combine(today, parsed, tzinfo=from_zone)
    target_dt = source_dt.astimezone(to_zone)
    return {
        "input": {"time": time_str, "location": from_location, "timezone": str(from_zone)},
        "output": {
            "time": target_dt.strftime("%H:%M"),
            "date": target_dt.strftime("%Y-%m-%d"),
            "location": to_location,
            "timezone": str(to_zone),
        },
    }
