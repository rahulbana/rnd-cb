"""Historical events on a given date (muffinlabs 'On this day', free, no key)."""
from __future__ import annotations

from .base import Tool, err, http_get_json, ok

HISTORY_URL = "http://history.muffinlabs.com/date/{month}/{day}"


def get_events_on_date(month: int, day: int, year: int | None = None,
                       limit: int = 15) -> dict:
    """Return notable historical events for a month/day, optionally filtered by year."""
    try:
        data = http_get_json(HISTORY_URL.format(month=month, day=day))
    except Exception:
        return err(f"Could not fetch events for {month}/{day}.")

    events = (data.get("data") or {}).get("Events") or []
    parsed = []
    for e in events:
        yr = e.get("year")
        try:
            yr_int = int(yr)
        except (TypeError, ValueError):
            yr_int = None
        if year is not None and yr_int != year:
            continue
        parsed.append({"year": yr, "event": e.get("text")})

    if year is not None and not parsed:
        return ok({
            "date": f"{month}/{day}/{year}",
            "count": 0,
            "events": [],
            "note": f"No notable events found for {month}/{day}/{year}.",
        })

    parsed = parsed[:limit]
    label = f"{month}/{day}" + (f"/{year}" if year else "")
    return ok({"date": label, "count": len(parsed), "events": parsed})


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="get_events_on_date",
            description="Get notable historical events that happened on a particular "
                        "date. Provide month and day; optionally a year to filter "
                        "(e.g. what happened on 21 July 1989).",
            category="Calendar",
            parameters={
                "type": "object",
                "properties": {
                    "month": {"type": "integer", "description": "Month number 1-12."},
                    "day": {"type": "integer", "description": "Day of month 1-31."},
                    "year": {"type": "integer", "description": "Optional year to filter events."},
                },
                "required": ["month", "day"],
            },
            func=get_events_on_date,
        )
    ]
