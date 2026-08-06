"""Currency converter (open.er-api.com, free, no key)."""
from __future__ import annotations

from .base import Tool, err, http_get_json, ok

RATES_URL = "https://open.er-api.com/v6/latest/{base}"


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount from one currency to another using live exchange rates."""
    base = from_currency.strip().upper()
    target = to_currency.strip().upper()
    try:
        data = http_get_json(RATES_URL.format(base=base))
    except Exception:
        return err(f"Could not fetch exchange rates for '{base}'.")
    if data.get("result") != "success":
        return err(f"Unknown or unsupported base currency '{base}'.")

    rates = data.get("rates", {})
    if target not in rates:
        return err(f"Unknown or unsupported target currency '{target}'.")

    rate = rates[target]
    converted = round(amount * rate, 4)
    return ok({
        "amount": amount,
        "from": base,
        "to": target,
        "rate": rate,
        "converted": converted,
        "as_of": data.get("time_last_update_utc"),
    })


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="convert_currency",
            description="Convert an amount of money from one currency to another "
                        "using live exchange rates (e.g. USD to INR).",
            category="Converters",
            parameters={
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount to convert."},
                    "from_currency": {"type": "string", "description": "3-letter code, e.g. USD."},
                    "to_currency": {"type": "string", "description": "3-letter code, e.g. INR."},
                },
                "required": ["amount", "from_currency", "to_currency"],
            },
            func=convert_currency,
        )
    ]
