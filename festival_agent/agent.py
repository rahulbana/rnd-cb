"""Core agent logic: turn a festival + year (or a free-form question) into a date.

The heavy lifting is done by an OpenAI model. We ask it to return a small,
strictly-typed JSON object so the rest of the program never has to parse prose.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - friendlier error than a traceback
    raise ImportError(
        "The 'openai' package is required. Install dependencies with "
        "`pip install -r requirements.txt`."
    ) from exc


DEFAULT_MODEL = "gpt-4o-mini"

# We force the model to answer with this exact shape. Structured output means we
# get a date we can rely on instead of a sentence we'd have to scrape.
_RESPONSE_SCHEMA = {
    "name": "festival_date",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "festival": {
                "type": "string",
                "description": "The canonical English name of the festival.",
            },
            "year": {
                "type": "integer",
                "description": "The year the question is about.",
            },
            "found": {
                "type": "boolean",
                "description": "True if a specific date could be determined.",
            },
            "date": {
                "type": "string",
                "description": (
                    "Primary/main day of the festival in ISO format YYYY-MM-DD. "
                    "Empty string if not found."
                ),
            },
            "date_range": {
                "type": "string",
                "description": (
                    "For multi-day festivals, the full span as a human string, "
                    "e.g. '1 Nov - 5 Nov 1984'. Empty string if single day."
                ),
            },
            "day_of_week": {
                "type": "string",
                "description": "Weekday of the primary date, e.g. 'Tuesday'.",
            },
            "notes": {
                "type": "string",
                "description": (
                    "Short caveats: regional variation, lunar-calendar uncertainty, "
                    "sighting-of-the-moon dependence, etc. May be empty."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "How confident the model is in the date.",
            },
        },
        "required": [
            "festival",
            "year",
            "found",
            "date",
            "date_range",
            "day_of_week",
            "notes",
            "confidence",
        ],
    },
}

_SYSTEM_PROMPT = (
    "You are a precise calendar assistant specialising in the dates of religious "
    "and cultural festivals (Hindu, Islamic, Christian, Sikh, Jewish, Buddhist and "
    "others) across history. Given a festival and a year, return the exact Gregorian "
    "calendar date on which it was celebrated.\n\n"
    "Rules:\n"
    "- Many festivals follow lunar or lunisolar calendars, so the Gregorian date "
    "changes every year. Compute the date for the specific year asked.\n"
    "- Islamic festivals (Eid al-Fitr, Eid al-Adha, etc.) historically depended on "
    "moon sighting and can vary by a day across regions. Note this in 'notes' and "
    "lower confidence accordingly.\n"
    "- For multi-day festivals (e.g. Diwali, Navratri), put the main day in 'date' "
    "and the full span in 'date_range'.\n"
    "- If you genuinely cannot determine the date, set 'found' to false and leave "
    "'date' empty rather than guessing.\n"
    "- Always reason about the correct year; do not default to the current year."
)


@dataclass
class FestivalResult:
    """A structured answer about when a festival fell in a given year."""

    festival: str
    year: int
    found: bool
    date: str
    date_range: str
    day_of_week: str
    notes: str
    confidence: str

    @classmethod
    def from_dict(cls, data: dict) -> "FestivalResult":
        return cls(
            festival=data.get("festival", ""),
            year=int(data.get("year", 0)),
            found=bool(data.get("found", False)),
            date=data.get("date", ""),
            date_range=data.get("date_range", ""),
            day_of_week=data.get("day_of_week", ""),
            notes=data.get("notes", ""),
            confidence=data.get("confidence", "low"),
        )


class FestivalAgent:
    """Thin wrapper around the OpenAI client for festival-date lookups."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional["OpenAI"] = None,
    ) -> None:
        self.model = model or os.getenv("FESTIVAL_AGENT_MODEL", DEFAULT_MODEL)
        if client is not None:
            self.client = client
        else:
            key = api_key or os.getenv("OPENAI_API_KEY")
            if not key:
                raise RuntimeError(
                    "No OpenAI API key found. Set OPENAI_API_KEY in your environment "
                    "or a .env file (see .env.example)."
                )
            self.client = OpenAI(api_key=key)

    def lookup(self, festival: str, year: int) -> FestivalResult:
        """Look up a festival by name and year."""
        user_msg = (
            f"On what Gregorian date was {festival} celebrated in the year {year}?"
        )
        return self._complete(user_msg)

    def ask(self, question: str) -> FestivalResult:
        """Answer a free-form question such as 'When was Holi in 1995?'."""
        return self._complete(question)

    def _complete(self, user_msg: str) -> FestivalResult:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_schema", "json_schema": _RESPONSE_SCHEMA},
        )
        payload = response.choices[0].message.content or "{}"
        return FestivalResult.from_dict(json.loads(payload))
