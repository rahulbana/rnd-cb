"""Age calculator (offline, using dateutil)."""
from __future__ import annotations

from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from .base import Tool, err, ok


def _parse_date(value: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def calculate_age(birth_date: str, as_of: str | None = None) -> dict:
    """Calculate age from a birth date, optionally as of a reference date."""
    bd = _parse_date(birth_date)
    if not bd:
        return err("Could not parse birth_date. Use a format like YYYY-MM-DD.")
    ref = _parse_date(as_of) if as_of else date.today()
    if ref is None:
        return err("Could not parse as_of date. Use a format like YYYY-MM-DD.")
    if bd > ref:
        return err("birth_date is after the reference date.")

    diff = relativedelta(ref, bd)
    total_days = (ref - bd).days
    return ok({
        "birth_date": bd.isoformat(),
        "as_of": ref.isoformat(),
        "years": diff.years,
        "months": diff.months,
        "days": diff.days,
        "human": f"{diff.years} years, {diff.months} months, {diff.days} days",
        "total_days": total_days,
        "total_weeks": total_days // 7,
    })


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="calculate_age",
            description="Calculate a person's age from their birth date, optionally "
                        "as of a specific reference date.",
            category="Calendar",
            parameters={
                "type": "object",
                "properties": {
                    "birth_date": {"type": "string", "description": "Birth date, e.g. 1990-05-21."},
                    "as_of": {"type": "string", "description": "Optional reference date."},
                },
                "required": ["birth_date"],
            },
            func=calculate_age,
        )
    ]
