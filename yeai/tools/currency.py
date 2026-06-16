"""Currency conversion tool (USD <-> GBP and any other pair).

Uses the free, key-less Exchange Rate API (https://open.er-api.com) to fetch
live mid-market rates. Common currency words ("dollar", "pound", ...) are
mapped to their ISO 4217 codes so the model can be a little loose with names.
"""

from __future__ import annotations

from typing import Dict

from .base import Tool
from .http import get_json

_API = "https://open.er-api.com/v6/latest/{base}"

# A few friendly aliases on top of raw ISO codes.
_ALIASES: Dict[str, str] = {
    "dollar": "USD",
    "dollars": "USD",
    "usd": "USD",
    "us$": "USD",
    "$": "USD",
    "pound": "GBP",
    "pounds": "GBP",
    "sterling": "GBP",
    "gbp": "GBP",
    "£": "GBP",
    "euro": "EUR",
    "euros": "EUR",
    "eur": "EUR",
    "€": "EUR",
    "yen": "JPY",
    "jpy": "JPY",
    "rupee": "INR",
    "rupees": "INR",
    "inr": "INR",
}


def _to_code(currency: str) -> str:
    key = currency.strip().lower()
    if key in _ALIASES:
        return _ALIASES[key]
    code = currency.strip().upper()
    if len(code) == 3 and code.isalpha():
        return code
    raise ValueError(
        f"Unrecognised currency: {currency!r}. Use an ISO code like 'USD' or "
        f"'GBP', or a name like 'dollar' / 'pound'."
    )


def _convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    base = _to_code(from_currency)
    target = _to_code(to_currency)

    if base == target:
        return f"{amount:g} {base} = {amount:g} {target} (same currency)"

    data = get_json(_API.format(base=base))
    if data.get("result") != "success":
        raise ValueError(f"Rate lookup failed for base currency {base}.")

    rates = data.get("rates", {})
    if target not in rates:
        raise ValueError(f"No exchange rate available for {target}.")

    rate = rates[target]
    converted = amount * rate
    updated = data.get("time_last_update_utc", "unknown time")
    return (
        f"{amount:g} {base} = {converted:,.2f} {target} "
        f"(rate 1 {base} = {rate:.4f} {target}; updated {updated})"
    )


CURRENCY_TOOL = Tool(
    name="convert_currency",
    description=(
        "Convert an amount of money from one currency to another using live "
        "exchange rates, e.g. US dollars to British pounds or pounds to "
        "dollars. Accepts ISO codes (USD, GBP, EUR, ...) or names (dollar, "
        "pound, euro, ...)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "amount": {
                "type": "number",
                "description": "How much to convert.",
            },
            "from_currency": {
                "type": "string",
                "description": "Currency to convert from (e.g. 'USD' or 'dollar').",
            },
            "to_currency": {
                "type": "string",
                "description": "Currency to convert to (e.g. 'GBP' or 'pound').",
            },
        },
        "required": ["amount", "from_currency", "to_currency"],
    },
    handler=_convert_currency,
)

TOOLS = [CURRENCY_TOOL]
