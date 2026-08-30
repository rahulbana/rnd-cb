"""Currency conversion tool (static reference rates).

Rates are indicative and labelled ESTIMATED; a live FX API can replace the
table behind the same interface without touching callers.
"""
from __future__ import annotations

from ..schemas.common import DataTrust, Freshness
from .base import Tool, ToolResult

# Indicative rates relative to 1 USD. Coarse and clearly labelled as estimates.
_USD_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 155.0,
    "INR": 83.0,
    "AUD": 1.52,
    "SGD": 1.35,
    "THB": 36.0,
    "AED": 3.67,
}


class CurrencyTool(Tool):
    name = "currency"
    description = "Convert an amount between currencies using indicative rates."

    async def run(self, *, amount: float, from_currency: str, to_currency: str, **_: object) -> ToolResult:
        src, dst = from_currency.upper(), to_currency.upper()
        if src not in _USD_RATES or dst not in _USD_RATES:
            return self._fail(f"unsupported currency pair {src}->{dst}")
        usd = amount / _USD_RATES[src]
        converted = round(usd * _USD_RATES[dst], 2)
        return ToolResult(
            tool=self.name,
            ok=True,
            trust=DataTrust.ESTIMATED,
            freshness=Freshness.DAYS,
            source="reference-rates",
            data={
                "amount": amount,
                "from": src,
                "to": dst,
                "converted": converted,
                "rate": round(_USD_RATES[dst] / _USD_RATES[src], 4),
            },
        )
