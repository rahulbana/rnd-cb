"""Budget tracking and hard caps that kill runaway research.

The `BudgetTracker` is carried in graph state and consulted by the reflection
router before every new iteration. Two independent limits apply:

  - iteration cap: max number of plan→search→read→reflect cycles
  - cost cap: cumulative estimated USD spend across all LLM + search calls

Cost is *estimated* from token counts using a per-model price table, plus a flat
per-search charge. Estimation is fine here — the cap exists to bound worst-case
spend, not to bill customers.
"""

from __future__ import annotations

from pydantic import BaseModel

# USD per 1M tokens (input, output). Update as pricing changes; unknown models
# fall back to a conservative default so we never under-count.
_PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-5": (15.0, 75.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}
_DEFAULT_PRICE = (5.0, 25.0)
_COST_PER_SEARCH = 0.004  # blended estimate across paid backends


class BudgetExceeded(Exception):
    """Raised (or signaled) when a hard cap is hit."""


class BudgetTracker(BaseModel):
    max_iterations: int = 5
    max_usd_cost: float = 2.50

    iterations: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    search_calls: int = 0
    llm_cost: float = 0.0
    search_cost: float = 0.0

    @property
    def usd_spent(self) -> float:
        return round(self.llm_cost + self.search_cost, 6)

    def record_llm(self, model: str, input_tokens: int, output_tokens: int) -> None:
        in_price, out_price = _PRICE_PER_MTOK.get(model, _DEFAULT_PRICE)
        cost = (input_tokens / 1_000_000) * in_price + (output_tokens / 1_000_000) * out_price
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.llm_cost = round(self.llm_cost + cost, 6)

    def record_searches(self, n: int) -> None:
        self.search_calls += n
        self.search_cost = round(self.search_cost + n * _COST_PER_SEARCH, 6)

    def start_iteration(self) -> None:
        self.iterations += 1

    # ── cap checks ──────────────────────────────────────────────────────────
    def iteration_cap_reached(self) -> bool:
        return self.iterations >= self.max_iterations

    def cost_cap_reached(self) -> bool:
        return self.usd_spent >= self.max_usd_cost

    def should_stop(self) -> bool:
        return self.iteration_cap_reached() or self.cost_cap_reached()

    def stop_reason(self) -> str | None:
        if self.cost_cap_reached():
            return f"cost cap reached (${self.usd_spent:.2f} ≥ ${self.max_usd_cost:.2f})"
        if self.iteration_cap_reached():
            return f"iteration cap reached ({self.iterations} ≥ {self.max_iterations})"
        return None

    def remaining_budget_fraction(self) -> float:
        """How much cost headroom is left, in [0, 1]. Used to taper fan-out late in a run."""
        if self.max_usd_cost <= 0:
            return 0.0
        return max(0.0, 1.0 - self.usd_spent / self.max_usd_cost)


class Usage(BaseModel):
    """Lightweight token-usage record returned alongside LLM calls."""

    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
