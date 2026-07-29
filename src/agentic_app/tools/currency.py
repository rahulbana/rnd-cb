"""Currency converter tool backed by a free, keyless FX rates endpoint.

Exposed as an OpenAI Agents `function_tool`. Uses open.er-api.com by default
(configurable via FX_API_BASE). Returns a JSON string.
"""

from __future__ import annotations

import json

import httpx
from agents import function_tool

from agentic_app.config import get_settings


@function_tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount from one currency to another using live exchange rates.

    Args:
        amount: The amount to convert (e.g. 100.0).
        from_currency: Source ISO 4217 currency code (e.g. "USD", "EUR", "INR").
        to_currency: Target ISO 4217 currency code.

    Returns:
        A JSON string with the converted amount, the rate used, and the rate date.
    """
    settings = get_settings()
    base = from_currency.strip().upper()
    target = to_currency.strip().upper()

    if amount < 0:
        return json.dumps({"error": "amount must be non-negative"})

    url = f"{settings.fx_api_base.rstrip('/')}/{base}"
    try:
        resp = httpx.get(url, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": f"failed to fetch FX rates: {exc}"})

    if data.get("result") == "error":
        return json.dumps({"error": data.get("error-type", "unknown FX error"), "base": base})

    rates = data.get("rates", {})
    rate = rates.get(target)
    if rate is None:
        return json.dumps({"error": f"unknown currency code: {target}", "base": base})

    converted = round(amount * rate, 4)
    return json.dumps(
        {
            "amount": amount,
            "from": base,
            "to": target,
            "rate": rate,
            "converted": converted,
            "rate_date": data.get("time_last_update_utc"),
        }
    )
