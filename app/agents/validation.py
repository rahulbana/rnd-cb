"""Validation agent: sanity-check the generated frame against its spec.

Runs a battery of cheap structural and statistical checks and returns a
:class:`ValidationReport`. Failing a check does not abort the pipeline — the
report is surfaced to the caller so they can decide what to do.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.agents.base import Agent
from app.models.artifacts import ValidationReport
from app.models.spec import DatasetSpec, DType, FeatureRole, TaskType


class ValidationAgent(Agent):
    name = "validation"

    def run(self, df: pd.DataFrame, spec: DatasetSpec) -> ValidationReport:
        checks: list[dict] = []

        # Row count (>= requested; duplicates can add rows).
        checks.append(
            self._check(
                "row_count",
                len(df) >= spec.n_rows,
                f"expected >= {spec.n_rows} rows, got {len(df)}",
            )
        )

        # Expected columns present.
        expected = {f.name for f in spec.features}
        if spec.target is not None:
            expected.add(spec.target.name)
        missing_cols = expected - set(df.columns)
        checks.append(
            self._check(
                "columns_present",
                not missing_cols,
                f"missing columns: {sorted(missing_cols)}" if missing_cols else "ok",
            )
        )

        # No duplicate column names.
        checks.append(
            self._check(
                "unique_column_names",
                df.columns.is_unique,
                "duplicate column names present",
            )
        )

        # Primary key uniqueness (before duplicate injection this holds; with
        # duplicates we only warn).
        id_cols = [f.name for f in spec.features if f.role == FeatureRole.ID]
        if id_cols and spec.quality.duplicate_rate == 0:
            col = id_cols[0]
            checks.append(
                self._check(
                    "primary_key_unique",
                    df[col].is_unique,
                    f"'{col}' is not unique",
                )
            )

        # Target sanity.
        if spec.target is not None and spec.target.name in df.columns:
            checks.extend(self._validate_target(df, spec))

        # Missingness is within a sane bound of what was requested.
        overall_missing = float(df.isna().mean().mean())
        checks.append(
            self._check(
                "missing_within_bounds",
                overall_missing <= spec.quality.missing_rate + 0.05,
                f"overall missing fraction {overall_missing:.3f}",
            )
        )

        # No constant feature columns (degenerate features).
        constant = [
            f.name
            for f in spec.features
            if f.role == FeatureRole.FEATURE
            and f.name in df.columns
            and df[f.name].nunique(dropna=True) <= 1
        ]
        checks.append(
            self._check(
                "no_constant_features",
                not constant,
                f"constant features: {constant}" if constant else "ok",
            )
        )

        passed = all(c["passed"] for c in checks)
        self.log(f"validation {'passed' if passed else 'FAILED'} ({len(checks)} checks)")
        return ValidationReport(passed=passed, checks=checks)

    def _validate_target(self, df: pd.DataFrame, spec: DatasetSpec) -> list[dict]:
        checks = []
        target = spec.target
        col = df[target.name]
        checks.append(
            self._check(
                "target_no_nulls", not col.isna().any(), "target contains nulls"
            )
        )
        if spec.task_type.is_classification:
            nunique = col.nunique()
            checks.append(
                self._check(
                    "target_has_multiple_classes",
                    nunique >= 2,
                    f"target has {nunique} class(es)",
                )
            )
            if spec.task_type == TaskType.BINARY_CLASSIFICATION:
                rate = float(pd.Series(col).astype("category").cat.codes.mean()) if col.dtype == object else float(np.mean(col))
                # Only a soft check; imbalance is intentional.
                checks.append(
                    self._check(
                        "target_not_degenerate",
                        0 < col.value_counts(normalize=True).min(),
                        "one class is empty",
                    )
                )
        return checks

    def _check(self, name: str, passed: bool, detail: str) -> dict:
        return {"name": name, "passed": bool(passed), "detail": detail}
