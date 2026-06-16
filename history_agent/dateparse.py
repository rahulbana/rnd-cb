"""Flexible parsing of user-supplied dates.

Two kinds of input are supported, distinguished automatically:

* A *full date* that includes a year, e.g. ``"7 July 1984"``, ``"7th July 1984"``,
  ``"1984-07-07"`` or ``"07/07/1984"``. We research what happened on that exact day.
* A *day + month* with no year, e.g. ``"21 July"``, ``"21st July"`` or ``"July 21"``.
  We research what historically happened on that day across all years
  ("this day in history").
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass

from dateutil import parser as _dateutil_parser

# A standalone 4-digit run is how we decide the user supplied a year. Months and
# days never have four digits, so this is a reliable signal across input formats.
_YEAR_RE = re.compile(r"\b\d{4}\b")


@dataclass(frozen=True)
class ParsedDate:
    """A normalised date request.

    Attributes:
        month: Month number, 1-12.
        day: Day of month, 1-31.
        year: The year if the user supplied one, otherwise ``None``.
    """

    month: int
    day: int
    year: int | None

    @property
    def has_year(self) -> bool:
        return self.year is not None

    @property
    def month_name(self) -> str:
        return calendar.month_name[self.month]

    @property
    def day_with_suffix(self) -> str:
        """The day rendered with an ordinal suffix, e.g. ``"21st"``."""
        if 10 <= self.day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(self.day % 10, "th")
        return f"{self.day}{suffix}"

    def human(self) -> str:
        """A human-readable rendering, with the year only when one was given."""
        base = f"{self.day_with_suffix} {self.month_name}"
        return f"{base} {self.year}" if self.has_year else base

    def slug(self) -> str:
        """A filesystem-friendly identifier used for default output filenames."""
        if self.has_year:
            return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        return f"{self.month_name.lower()}-{self.day:02d}"


class DateParseError(ValueError):
    """Raised when the supplied text cannot be understood as a date."""


def parse_date_input(text: str) -> ParsedDate:
    """Parse free-form date text into a :class:`ParsedDate`.

    Args:
        text: User input such as ``"7 July 1984"`` or ``"21 July"``.

    Returns:
        A :class:`ParsedDate`. ``year`` is ``None`` when no year was supplied.

    Raises:
        DateParseError: If the text cannot be interpreted as a date.
    """
    raw = (text or "").strip()
    if not raw:
        raise DateParseError("No date was provided.")

    has_year = bool(_YEAR_RE.search(raw))

    # `default` supplies fields the input omits. By parsing twice against two
    # different defaults we can tell which fields dateutil actually filled in,
    # which guards against ambiguous input silently inheriting today's day/month.
    try:
        probe_a = _dateutil_parser.parse(raw, default=_DEFAULT_A, dayfirst=True)
        probe_b = _dateutil_parser.parse(raw, default=_DEFAULT_B, dayfirst=True)
    except (ValueError, OverflowError) as exc:
        raise DateParseError(f"Could not understand the date {raw!r}.") from exc

    if probe_a.month != probe_b.month or probe_a.day != probe_b.day:
        raise DateParseError(
            f"The date {raw!r} is ambiguous — please include at least a day and a month."
        )

    month, day = probe_a.month, probe_a.day
    year = probe_a.year if has_year else None

    # Validate the day is legal for the month (e.g. reject 31 February). For a
    # yearless date we check against a leap year so 29 February is allowed.
    check_year = year if year is not None else 2000
    max_day = calendar.monthrange(check_year, month)[1]
    if day > max_day:
        raise DateParseError(
            f"{calendar.month_name[month]} does not have {day} days"
            + (f" in {year}." if year is not None else ".")
        )

    return ParsedDate(month=month, day=day, year=year)


# Two sentinel defaults that differ in every field. After parsing, any field that
# still matches both defaults was supplied by the user; a field that changed was
# defaulted. We only rely on month/day agreement here, but distinct values keep
# the comparison robust.
_DEFAULT_A = _dateutil_parser.parse("2000-05-15 00:00:00")
_DEFAULT_B = _dateutil_parser.parse("2004-09-20 00:00:00")
