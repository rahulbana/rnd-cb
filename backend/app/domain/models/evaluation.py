"""Evaluation domain models: cases and scorecards."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """One graded example: a question, the produced answer, its contexts."""

    question: str
    answer: str
    contexts: list[str] = Field(default_factory=list)
    ground_truth: str | None = None


class MetricScore(BaseModel):
    name: str
    score: float
    passed: bool


class Scorecard(BaseModel):
    """Aggregate eval result with a pass/fail threshold."""

    metrics: list[MetricScore]
    threshold: float
    passed: bool
    cases: int
    harness: str

    def metric(self, name: str) -> float:
        for m in self.metrics:
            if m.name == name:
                return m.score
        return 0.0
