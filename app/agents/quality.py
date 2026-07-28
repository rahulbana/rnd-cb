"""Data quality agent: inject controlled, realistic imperfections.

Real-world datasets are never clean. This agent degrades the pristine generated
frame in reproducible, rate-controlled ways so downstream code (and models) can
be tested against missingness, duplicates, outliers, and noise. Feature columns
are degraded; the target and the primary key are left intact.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.agents.base import Agent
from app.models.spec import DatasetSpec, DType, FeatureRole


class QualityAgent(Agent):
    name = "quality"

    def run(
        self, df: pd.DataFrame, spec: DatasetSpec, rng: np.random.Generator
    ) -> pd.DataFrame:
        q = spec.quality
        protected = self._protected_columns(spec)
        feature_cols = [c for c in df.columns if c not in protected]

        if q.noise > 0:
            self._inject_noise(df, spec, q.noise, rng)
        if q.outlier_rate > 0:
            self._inject_outliers(df, spec, q.outlier_rate, rng)
        if q.missing_rate > 0:
            self._inject_missing(df, feature_cols, q.missing_rate, rng)
        if q.duplicate_rate > 0:
            df = self._inject_duplicates(df, q.duplicate_rate, rng)

        self.log(
            f"quality injected missing={q.missing_rate} dup={q.duplicate_rate} "
            f"outlier={q.outlier_rate} noise={q.noise}"
        )
        return df

    def _protected_columns(self, spec: DatasetSpec) -> set[str]:
        protected = {
            f.name for f in spec.features if f.role in {FeatureRole.ID, FeatureRole.TIME}
        }
        if spec.target is not None:
            protected.add(spec.target.name)
        protected.add("timestamp")
        return protected

    def _numeric_feature_cols(self, df: pd.DataFrame, spec: DatasetSpec) -> list[str]:
        return [
            f.name
            for f in spec.features
            if f.role == FeatureRole.FEATURE
            and f.dtype in {DType.FLOAT, DType.INTEGER}
            and f.name in df.columns
        ]

    def _inject_noise(
        self, df: pd.DataFrame, spec: DatasetSpec, level: float, rng: np.random.Generator
    ) -> None:
        for col in self._numeric_feature_cols(df, spec):
            values = df[col].astype(float)
            std = values.std()
            if std == 0:
                continue
            df[col] = values + rng.normal(0, level * std, len(df))

    def _inject_outliers(
        self, df: pd.DataFrame, spec: DatasetSpec, rate: float, rng: np.random.Generator
    ) -> None:
        n = len(df)
        for col in self._numeric_feature_cols(df, spec):
            k = int(rate * n)
            if k == 0:
                continue
            idx = rng.choice(n, size=k, replace=False)
            values = df[col].astype(float)
            std = values.std() or 1.0
            direction = rng.choice([-1, 1], size=k)
            values.iloc[idx] = (
                values.iloc[idx].to_numpy()
                + direction * rng.uniform(6, 12, k) * std
            )
            # Rebuild the whole column (rather than an in-place typed setitem,
            # which raises on int columns under pandas 3) and preserve integer
            # dtype by rounding.
            if pd.api.types.is_integer_dtype(df[col].dtype):
                df[col] = np.round(values).astype("int64")
            else:
                df[col] = values

    def _inject_missing(
        self, df: pd.DataFrame, cols: list[str], rate: float, rng: np.random.Generator
    ) -> None:
        n = len(df)
        for col in cols:
            mask = rng.random(n) < rate
            if mask.any():
                # Series.mask upcasts the column as needed to hold NaN (e.g.
                # bool -> object, int -> float). A direct df.loc[...] = np.nan
                # raises on bool/int columns under pandas 3's strict dtype rules.
                df[col] = df[col].mask(mask)

    def _inject_duplicates(
        self, df: pd.DataFrame, rate: float, rng: np.random.Generator
    ) -> pd.DataFrame:
        n = len(df)
        k = int(rate * n)
        if k == 0:
            return df
        idx = rng.choice(n, size=k, replace=True)
        dupes = df.iloc[idx].copy()
        out = pd.concat([df, dupes], ignore_index=True)
        # Shuffle so duplicates are not all at the end.
        order = rng.permutation(len(out))
        return out.iloc[order].reset_index(drop=True)
