"""Unit / measurement converter (offline, using Pint)."""
from __future__ import annotations

from .base import Tool, err, ok

# A single shared registry is recommended by Pint.
try:
    from pint import UnitRegistry

    _ureg = UnitRegistry()
except Exception:  # pragma: no cover - pint should always be present
    _ureg = None


def convert_measurement(value: float, from_unit: str, to_unit: str) -> dict:
    """Convert a physical quantity between units, e.g. 100 cm -> meters."""
    if _ureg is None:
        return err("Measurement conversion is unavailable (pint not installed).")
    try:
        quantity = value * _ureg(from_unit)
        result = quantity.to(to_unit)
    except Exception as exc:
        return err(f"Could not convert {value} {from_unit} to {to_unit}: {exc}")
    return ok({
        "value": value,
        "from_unit": from_unit,
        "to_unit": to_unit,
        "result": round(result.magnitude, 8),
        "result_str": f"{round(result.magnitude, 8)} {to_unit}",
    })


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="convert_measurement",
            description="Convert a measurement from one unit to another, e.g. "
                        "'100 cm' to 'meter', '5 mile' to 'km', '2 hours' to 'minutes'.",
            category="Converters",
            parameters={
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "Numeric value to convert."},
                    "from_unit": {"type": "string", "description": "Source unit, e.g. 'cm'."},
                    "to_unit": {"type": "string", "description": "Target unit, e.g. 'meter'."},
                },
                "required": ["value", "from_unit", "to_unit"],
            },
            func=convert_measurement,
        )
    ]
