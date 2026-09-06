"""EvalHarness port -- scores the RAG pipeline against a golden set."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.domain.models import EvalCase, Scorecard

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class EvalHarness(Protocol):
    """Any evaluation backend (RAGAS, DeepEval, heuristic) must satisfy this."""

    name: str  # "heuristic" | "ragas" | "deepeval" | ...

    @classmethod
    def from_settings(cls, settings: Settings) -> EvalHarness:
        """Construct the adapter from application settings."""
        ...

    async def evaluate(self, cases: Sequence[EvalCase], *, threshold: float) -> Scorecard:
        """Score cases (faithfulness, relevancy, context precision/recall)."""
        ...
