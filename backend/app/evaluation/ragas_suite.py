"""Evaluation harness placeholder.

Phase 9 wires RAGAS/DeepEval against a golden Q&A set and runs it in CI. The
module exists now so the package boundary is fixed from Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalResult:
    """A single metric outcome from an eval run."""

    metric: str
    score: float
    passed: bool


def run_eval_suite() -> list[EvalResult]:
    """Placeholder -- returns an empty scorecard until Phase 9."""
    return []
