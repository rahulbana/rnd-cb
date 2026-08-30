"""Currency conversion tool.

Primary source: **Frankfurter** (European Central Bank reference rates, keyless).
Falls back to a static indicative table when the API is unreachable/offline.
"""
from __future__ import annotations

from ..config.settings import get_settings
from ..schemas.common import DataTrust, Freshness
from .base import Tool, ToolResult
from .http import get_json

_FRANKFURTER_URL = "https://api.frankfurter.app/latest"

# Static fallback rates relative to 1 USD.
_USD_RATES: dict[str, float] = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 155.0, "INR": 83.0,
    "AUD": 1.52, "SGD": 1.35, "THB": 36.0, "AED": 3.67,
}


class CurrencyTool(Tool):
    name = "currency"
    description = "Convert between currencies (ECB reference rates via Frankfurter)."

    async def run(self, *, amount: float, from_currency: str, to_currency: str, **_: object) -> ToolResult:
        src, dst = from_currency.upper(), to_currency.upper()
        if src == dst:
            return self._result(amount, src, dst, 1.0, DataTrust.VERIFIED,
                                Freshness.STATIC, "identity")

        settings = get_settings()
        if settings.enable_live_data:
            live = await self._live(amount, src, dst)
            if live is not None:
                return live
        return self._fallback(amount, src, dst)

    async def _live(self, amount: float, src: str, dst: str) -> ToolResult | None:
        data = await get_json(_FRANKFURTER_URL, params={"from": src, "to": dst}, ttl=6 * 3600)
        if not data or "rates" not in data or dst not in data["rates"]:
            return None
        rate = float(data["rates"][dst])
        return self._result(amount, src, dst, rate, DataTrust.LIVE,
                            Freshness.DAYS, "frankfurter/ecb")

    def _fallback(self, amount: float, src: str, dst: str) -> ToolResult:
        if src not in _USD_RATES or dst not in _USD_RATES:
            return self._fail(f"unsupported currency pair {src}->{dst}")
        rate = _USD_RATES[dst] / _USD_RATES[src]
        return self._result(amount, src, dst, rate, DataTrust.ESTIMATED,
                            Freshness.DAYS, "reference-rates")

    def _result(self, amount: float, src: str, dst: str, rate: float,
                trust: DataTrust, freshness: Freshness, source: str) -> ToolResult:
        return ToolResult(
            tool=self.name, ok=True, trust=trust, freshness=freshness, source=source,
            data={"amount": amount, "from": src, "to": dst,
                  "converted": round(amount * rate, 2), "rate": round(rate, 6)},
        )
