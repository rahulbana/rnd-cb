"""Heuristic evaluation harness.

Lexical, deterministic proxies for the RAGAS metrics -- no LLM or network, so it
runs in CI and gives a fast pass/fail signal. RAGAS/DeepEval (LLM-judged) plug
in behind the same port for higher-fidelity scoring.

- faithfulness: is the answer grounded in the retrieved context?
- answer_relevancy: does the answer address the question?
- context_precision: are the retrieved contexts on-topic for the answer?
- context_recall: do the contexts cover the ground truth?
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.domain.models import EvalCase, MetricScore, Scorecard

if TYPE_CHECKING:
    from app.core.config import Settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the",
    "a",
    "an",
    "of",
    "to",
    "in",
    "is",
    "and",
    "or",
    "for",
    "on",
    "at",
    "by",
    "with",
    "as",
    "it",
    "that",
    "this",
    "what",
    "which",
    "was",
    "are",
    "be",
    "from",
    "how",
    "why",
    "do",
    "does",
}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP}


def _coverage(target: set[str], source: set[str]) -> float:
    if not target:
        return 1.0
    return len(target & source) / len(target)


class HeuristicEvalHarness:
    """Lexical-overlap scoring of RAG cases."""

    name = "heuristic"

    @classmethod
    def from_settings(cls, settings: Settings) -> HeuristicEvalHarness:
        return cls()

    async def evaluate(self, cases: Sequence[EvalCase], *, threshold: float) -> Scorecard:
        faith: list[float] = []
        relevancy: list[float] = []
        precision: list[float] = []
        recall: list[float] = []

        for case in cases:
            answer = _tokens(case.answer)
            question = _tokens(case.question)
            context = (
                set().union(*(_tokens(c) for c in case.contexts))
                if case.contexts
                else set()
            )
            truth = _tokens(case.ground_truth or "")

            faith.append(_coverage(answer, context))
            relevancy.append(_coverage(question, answer))
            if case.contexts:
                on_topic = sum(1 for c in case.contexts if _tokens(c) & (truth or answer))
                precision.append(on_topic / len(case.contexts))
            else:
                precision.append(0.0)
            recall.append(_coverage(truth, context) if truth else 1.0)

        def mean(xs: list[float]) -> float:
            return sum(xs) / len(xs) if xs else 0.0

        metrics = [
            MetricScore(
                name="faithfulness", score=mean(faith), passed=mean(faith) >= threshold
            ),
            MetricScore(
                name="answer_relevancy",
                score=mean(relevancy),
                passed=mean(relevancy) >= threshold,
            ),
            MetricScore(
                name="context_precision",
                score=mean(precision),
                passed=mean(precision) >= threshold,
            ),
            MetricScore(
                name="context_recall",
                score=mean(recall),
                passed=mean(recall) >= threshold,
            ),
        ]
        return Scorecard(
            metrics=metrics,
            threshold=threshold,
            passed=all(m.passed for m in metrics),
            cases=len(cases),
            harness=self.name,
        )
