"""Per-request cost estimation.

A small, editable price table (USD per 1K tokens). Unknown provider/model pairs
cost 0 (local models like Ollama are free). Phase 9's analytics dashboard reads
the same estimates.
"""

from __future__ import annotations

# provider -> (input $/1K, output $/1K). Local providers are free.
_PRICING: dict[str, tuple[float, float]] = {
    "openai": (0.00015, 0.0006),  # gpt-4o-mini class
    "anthropic": (0.003, 0.015),  # sonnet class
    "gemini": (0.000075, 0.0003),  # flash class
    "ollama": (0.0, 0.0),
    "fake": (0.0, 0.0),
}


def estimate_cost(provider: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate request cost in USD from token counts."""
    in_rate, out_rate = _PRICING.get(provider, (0.0, 0.0))
    return (tokens_in / 1000.0) * in_rate + (tokens_out / 1000.0) * out_rate
