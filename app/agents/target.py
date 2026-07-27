"""Target agent: synthesise a label with genuine, controllable signal.

The label is a function of the feature columns (plus tunable noise), so a model
trained on the data actually has something to learn. ``signal_strength`` in the
:class:`TargetSpec` interpolates between "pure signal" (perfectly learnable) and
"pure noise" (unlearnable), which lets callers dial the difficulty and keeps the
ML-readiness score meaningful.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.agents.base import Agent
from app.models.spec import DatasetSpec, DType, FeatureRole, TaskType


class TargetAgent(Agent):
    name = "target"

    def run(
        self, df: pd.DataFrame, spec: DatasetSpec, rng: np.random.Generator
    ) -> pd.DataFrame:
        if spec.target is None:
            return df

        task = spec.task_type
        if task == TaskType.CLUSTERING:
            df[spec.target.name] = self._clusters(df, spec, rng)
        elif task == TaskType.TIME_SERIES:
            df = self._time_series(df, spec, rng)
        elif task.is_regression:
            df[spec.target.name] = self._regression(df, spec, rng)
        else:
            df[spec.target.name] = self._classification(df, spec, rng)
        self.log(f"generated target '{spec.target.name}' for {task.value}")
        return df

    # -- helpers ----------------------------------------------------------
    def _signal_score(
        self, df: pd.DataFrame, spec: DatasetSpec, rng: np.random.Generator
    ) -> np.ndarray:
        """Standardised linear score built from the feature columns."""

        n = len(df)
        score = np.zeros(n, dtype=float)
        for feature in spec.features:
            if feature.role != FeatureRole.FEATURE:
                continue
            col = df[feature.name]
            weight = rng.normal(0, 1)
            if feature.dtype in {DType.FLOAT, DType.INTEGER}:
                values = col.astype(float).to_numpy()
                std = values.std()
                if std == 0:
                    continue
                z = (values - values.mean()) / std
                score += weight * z
            elif feature.dtype in {DType.CATEGORY, DType.ORDINAL}:
                # Assign each category a random numeric effect (target encoding).
                cats = col.astype("category")
                effects = rng.normal(0, 1, len(cats.cat.categories))
                mapping = dict(zip(cats.cat.categories, effects))
                score += weight * col.map(mapping).astype(float).to_numpy()
            elif feature.dtype == DType.BOOLEAN:
                score += weight * col.astype(float).to_numpy()

        if spec.target and spec.target.nonlinear and score.std() > 0:
            z = (score - score.mean()) / score.std()
            score = z + 0.6 * np.sin(2.0 * z) + 0.4 * z**2

        if score.std() == 0:
            return rng.normal(0, 1, n)
        return (score - score.mean()) / score.std()

    def _blended_latent(
        self, df: pd.DataFrame, spec: DatasetSpec, rng: np.random.Generator
    ) -> np.ndarray:
        score = self._signal_score(df, spec, rng)
        noise = rng.normal(0, 1, len(df))
        s = spec.target.signal_strength if spec.target else 0.7
        latent = s * score + (1 - s) * noise
        return latent

    def _classification(
        self, df: pd.DataFrame, spec: DatasetSpec, rng: np.random.Generator
    ) -> np.ndarray:
        latent = self._blended_latent(df, spec, rng)
        target = spec.target
        assert target is not None

        if spec.task_type == TaskType.MULTICLASS_CLASSIFICATION and target.n_classes > 2:
            # Build several competing linear scores; argmax picks the class.
            k = target.n_classes
            scores = np.column_stack(
                [self._blended_latent(df, spec, rng) for _ in range(k)]
            )
            labels = scores.argmax(axis=1)
            if target.class_names and len(target.class_names) == k:
                names = np.array(target.class_names)
                return names[labels]
            return np.array([f"class_{i}" for i in labels])

        # Binary: threshold the latent at the quantile that yields positive_rate.
        rate = float(np.clip(target.positive_rate, 0.001, 0.999))
        threshold = np.quantile(latent, 1 - rate)
        positive = (latent >= threshold).astype(int)
        if target.class_names and len(target.class_names) == 2:
            return np.where(positive == 1, target.class_names[1], target.class_names[0])
        return positive

    def _regression(
        self, df: pd.DataFrame, spec: DatasetSpec, rng: np.random.Generator
    ) -> np.ndarray:
        score = self._signal_score(df, spec, rng)
        target = spec.target
        assert target is not None
        signal = target.signal_strength
        noise = rng.normal(0, 1, len(df))
        latent = signal * score + (1 - signal) * noise
        # Map onto a positive, interpretable scale.
        base = 100.0
        values = base + 25.0 * latent
        values = np.maximum(values, 0.0)
        return np.round(values, 2)

    def _clusters(
        self, df: pd.DataFrame, spec: DatasetSpec, rng: np.random.Generator
    ) -> np.ndarray:
        """Ground-truth cluster labels from a KMeans over numeric features."""

        numeric = [
            f.name
            for f in spec.features
            if f.dtype in {DType.FLOAT, DType.INTEGER}
            and f.role == FeatureRole.FEATURE
        ]
        k = spec.target.n_classes if spec.target else 4
        if not numeric:
            return rng.integers(0, k, len(df))
        try:
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler

            x = StandardScaler().fit_transform(df[numeric].astype(float))
            labels = KMeans(n_clusters=k, n_init=10, random_state=spec.random_seed).fit_predict(x)
            return np.array([f"segment_{i}" for i in labels])
        except Exception:  # pragma: no cover
            return rng.integers(0, k, len(df))

    def _time_series(
        self, df: pd.DataFrame, spec: DatasetSpec, rng: np.random.Generator
    ) -> pd.DataFrame:
        n = len(df)
        t = np.arange(n)
        trend = 0.02 * t
        seasonality = 10 * np.sin(2 * np.pi * t / 24.0)
        signal_from_features = 5 * self._signal_score(df, spec, rng)
        noise = rng.normal(0, 2, n)
        s = spec.target.signal_strength if spec.target else 0.7
        value = (
            50
            + trend
            + seasonality
            + s * signal_from_features
            + (1 - s) * noise * 5
        )
        name = spec.target.name if spec.target else "value"
        df[name] = np.round(value, 3)
        # Provide an explicit time index column.
        if "timestamp" not in df.columns:
            df.insert(
                0,
                "timestamp",
                pd.date_range("2023-01-01", periods=n, freq="h"),
            )
        return df
