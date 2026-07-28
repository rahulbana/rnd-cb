"""Result objects produced by the generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.models.spec import DatasetSpec


@dataclass
class ValidationReport:
    passed: bool
    checks: list[dict[str, Any]] = field(default_factory=list)

    @property
    def failures(self) -> list[dict[str, Any]]:
        return [c for c in self.checks if not c.get("passed", True)]


@dataclass
class EvaluationReport:
    task_type: str
    baseline_model: str
    metrics: dict[str, float] = field(default_factory=dict)
    ml_readiness_score: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    """Everything a single run produces."""

    spec: DatasetSpec
    data: pd.DataFrame
    data_dictionary: list[dict[str, Any]] = field(default_factory=list)
    eda: dict[str, Any] = field(default_factory=dict)
    validation: ValidationReport | None = None
    evaluation: EvaluationReport | None = None
    exports: dict[str, str] = field(default_factory=dict)
    output_dir: str | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.spec.name,
            "task_type": self.spec.task_type.value,
            "rows": len(self.data),
            "columns": list(self.data.columns),
            "output_dir": self.output_dir,
            "validation_passed": self.validation.passed if self.validation else None,
            "ml_readiness_score": (
                self.evaluation.ml_readiness_score if self.evaluation else None
            ),
            "exports": self.exports,
        }
