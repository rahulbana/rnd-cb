"""EDA agent: compute an exploratory-data-analysis summary.

Returns a JSON-serialisable dict (numeric summaries, correlations, missingness,
target distribution). Rendering to HTML/plots is the exporter/documentation
agents' job; this stays pure-data so it is easy to test and cheap to compute.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.agents.base import Agent
from app.models.spec import DatasetSpec, DType, FeatureRole


class EDAAgent(Agent):
    name = "eda"

    def run(self, df: pd.DataFrame, spec: DatasetSpec) -> dict:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        report: dict = {
            "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "missing": self._missing(df),
            "numeric_summary": self._numeric_summary(df, numeric_cols),
            "categorical_summary": self._categorical_summary(df, spec),
            "correlations": self._top_correlations(df, numeric_cols),
            "duplicate_rows": int(df.duplicated().sum()),
        }
        if spec.target is not None and spec.target.name in df.columns:
            report["target"] = self._target_summary(df, spec)
        self.log("EDA report computed")
        return report

    def _missing(self, df: pd.DataFrame) -> dict:
        frac = df.isna().mean()
        return {c: round(float(v), 4) for c, v in frac.items() if v > 0}

    def _numeric_summary(self, df: pd.DataFrame, cols: list[str]) -> dict:
        summary = {}
        for c in cols:
            s = df[c].dropna()
            if s.empty:
                continue
            summary[c] = {
                "count": int(s.count()),
                "mean": round(float(s.mean()), 4),
                "std": round(float(s.std()), 4),
                "min": round(float(s.min()), 4),
                "q25": round(float(s.quantile(0.25)), 4),
                "median": round(float(s.median()), 4),
                "q75": round(float(s.quantile(0.75)), 4),
                "max": round(float(s.max()), 4),
                "skew": round(float(s.skew()), 4),
            }
        return summary

    def _categorical_summary(self, df: pd.DataFrame, spec: DatasetSpec) -> dict:
        summary = {}
        cat_cols = [
            f.name
            for f in spec.features
            if f.dtype in {DType.CATEGORY, DType.ORDINAL} and f.name in df.columns
        ]
        for c in cat_cols:
            counts = df[c].value_counts(normalize=True).head(10)
            summary[c] = {
                "n_unique": int(df[c].nunique()),
                "top_values": {str(k): round(float(v), 4) for k, v in counts.items()},
            }
        return summary

    def _top_correlations(
        self, df: pd.DataFrame, cols: list[str], top: int = 10
    ) -> list[dict]:
        if len(cols) < 2:
            return []
        corr = df[cols].corr(numeric_only=True)
        pairs = []
        seen = set()
        for a in cols:
            for b in cols:
                if a == b or (b, a) in seen:
                    continue
                seen.add((a, b))
                val = corr.loc[a, b]
                if pd.notna(val):
                    pairs.append({"a": a, "b": b, "corr": round(float(val), 4)})
        pairs.sort(key=lambda p: abs(p["corr"]), reverse=True)
        return pairs[:top]

    def _target_summary(self, df: pd.DataFrame, spec: DatasetSpec) -> dict:
        col = df[spec.target.name]
        # Categorical target: classification labels or clustering segments.
        if spec.task_type.is_classification or not pd.api.types.is_numeric_dtype(col):
            dist = col.value_counts(normalize=True)
            return {
                "type": "clustering" if not spec.task_type.is_supervised else "classification",
                "n_classes": int(col.nunique()),
                "distribution": {str(k): round(float(v), 4) for k, v in dist.items()},
            }
        s = col.dropna().astype(float)
        return {
            "type": "regression",
            "mean": round(float(s.mean()), 4),
            "std": round(float(s.std()), 4),
            "min": round(float(s.min()), 4),
            "max": round(float(s.max()), 4),
        }
