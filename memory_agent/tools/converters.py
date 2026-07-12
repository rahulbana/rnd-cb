"""Currency and unit conversion tools."""

from __future__ import annotations

import requests
from langchain_core.tools import tool

from .base import HTTP_TIMEOUT


def make_converter_tools() -> list:
    ureg = None  # lazily-created pint registry (import is a little slow)

    @tool
    def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
        """Convert an amount between currencies using live exchange rates.

        Currencies are ISO codes, e.g. USD, EUR, INR, JPY.
        """
        src, dst = from_currency.upper().strip(), to_currency.upper().strip()
        try:
            resp = requests.get(
                f"https://open.er-api.com/v6/latest/{src}", timeout=HTTP_TIMEOUT
            )
            data = resp.json()
        except Exception as exc:
            return f"Currency lookup failed: {exc}"

        if data.get("result") != "success":
            return f"Could not fetch rates for {src} ({data.get('error-type', 'unknown error')})."
        rate = data.get("rates", {}).get(dst)
        if rate is None:
            return f"Unknown target currency: {dst}."
        return f"{amount:,.2f} {src} = {amount * rate:,.2f} {dst} (rate {rate:.4f})"

    @tool
    def convert_units(value: float, from_unit: str, to_unit: str) -> str:
        """Convert a value between physical units.

        Handles length, mass, temperature, volume, speed, time, data, etc.
        Examples: (10, "km", "mi"), (72, "degF", "degC"), (5, "kg", "lb").
        """
        nonlocal ureg
        try:
            if ureg is None:
                from pint import UnitRegistry

                ureg = UnitRegistry()
            result = ureg.Quantity(value, from_unit).to(to_unit)
        except Exception as exc:
            return f"Could not convert {value} {from_unit} to {to_unit}: {exc}"
        return f"{value} {from_unit} = {result.magnitude:.6g} {to_unit}"

    return [convert_currency, convert_units]
