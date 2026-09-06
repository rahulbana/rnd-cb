"""RAGAS evaluation harness (LLM-judged).

Higher-fidelity than the heuristic harness: faithfulness, answer relevancy, and
context precision/recall as computed by RAGAS. Heavy deps + an LLM judge, so
the import is lazy and this is opt-in.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.domain.models import EvalCase, MetricScore, Scorecard

if TYPE_CHECKING:
    from app.core.config import Settings

_METRIC_NAMES = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]


class RagasEvalHarness:
    """Scores RAG cases with RAGAS."""

    name = "ragas"

    @classmethod
    def from_settings(cls, settings: Settings) -> RagasEvalHarness:
        return cls()

    async def evaluate(self, cases: Sequence[EvalCase], *, threshold: float) -> Scorecard:
        from datasets import Dataset  # lazy import
        from ragas import evaluate  # lazy import
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        dataset = Dataset.from_dict(
            {
                "question": [c.question for c in cases],
                "answer": [c.answer for c in cases],
                "contexts": [c.contexts for c in cases],
                "ground_truth": [c.ground_truth or "" for c in cases],
            }
        )
        result = evaluate(
            dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ],
        )
        scores = {name: float(result[name]) for name in _METRIC_NAMES if name in result}
        metrics = [
            MetricScore(name=name, score=score, passed=score >= threshold)
            for name, score in scores.items()
        ]
        return Scorecard(
            metrics=metrics,
            threshold=threshold,
            passed=all(m.passed for m in metrics),
            cases=len(cases),
            harness=self.name,
        )
