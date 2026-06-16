"""Length unit conversion tool (centimetre <-> metre, and friends).

Conversions are done by expressing every supported unit in metres and then
scaling to the target unit, so any pair of supported units can be converted.
"""

from __future__ import annotations

from typing import Dict

from .base import Tool

# How many metres one of each unit represents.
_TO_METRES: Dict[str, float] = {
    "mm": 0.001,
    "millimeter": 0.001,
    "millimetre": 0.001,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimetre": 0.01,
    "m": 1.0,
    "meter": 1.0,
    "metre": 1.0,
    "km": 1000.0,
    "kilometer": 1000.0,
    "kilometre": 1000.0,
    "in": 0.0254,
    "inch": 0.0254,
    "ft": 0.3048,
    "foot": 0.3048,
    "feet": 0.3048,
    "yd": 0.9144,
    "yard": 0.9144,
    "mi": 1609.344,
    "mile": 1609.344,
}


def _normalise(unit: str) -> str:
    key = unit.strip().lower().rstrip("s") if unit else ""
    # Re-add the plural form for units stored without an 's' (e.g. "feet").
    if key not in _TO_METRES and (key + "s") in _TO_METRES:
        key += "s"
    if key not in _TO_METRES:
        # try the raw, un-stripped value too
        raw = unit.strip().lower()
        if raw in _TO_METRES:
            return raw
        raise ValueError(
            f"Unsupported length unit: {unit!r}. Supported units: "
            f"{', '.join(sorted(set(_TO_METRES)))}."
        )
    return key


def _convert_length(value: float, from_unit: str, to_unit: str) -> str:
    src = _normalise(from_unit)
    dst = _normalise(to_unit)
    metres = value * _TO_METRES[src]
    result = metres / _TO_METRES[dst]
    return f"{value} {from_unit} = {result:g} {to_unit}"


LENGTH_TOOL = Tool(
    name="convert_length",
    description=(
        "Convert a length from one unit to another, e.g. centimetre to metre "
        "or metre to centimetre. Supported units: mm, cm, m, km, inch, foot, "
        "yard and mile (singular or plural spellings accepted)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "value": {
                "type": "number",
                "description": "The numeric quantity to convert.",
            },
            "from_unit": {
                "type": "string",
                "description": "The unit to convert from (e.g. 'cm').",
            },
            "to_unit": {
                "type": "string",
                "description": "The unit to convert to (e.g. 'm').",
            },
        },
        "required": ["value", "from_unit", "to_unit"],
    },
    handler=_convert_length,
)

TOOLS = [LENGTH_TOOL]
