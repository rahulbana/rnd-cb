"""ML evaluation agent: train a baseline model and score ML-readiness.

Fits a quick baseline (random forest / logistic / linear) on a train/test split,
reports task-appropriate metrics, and rolls them into a single 0-100
ML-readiness score that also accounts for data completeness. The score answers
"is this dataset actually usable for modelling?" at a glance.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from app.agents.base import Agent
from app.models.artifacts import EvaluationReport
from app.models.spec import DatasetSpec, DType, FeatureRole, TaskType


class EvaluationAgent(Agent):
    name = "evaluation"

    def run(self, df: pd.DataFrame, spec: DatasetSpec) -> EvaluationReport:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                return self._evaluate(df, spec)
            except Exception as exc:  # pragma: no cover - defensive
                return EvaluationReport(
                    task_type=spec.task_type.value,
                    baseline_model="none",
                    notes=[f"evaluation skipped: {exc}"],
                )

    def _feature_frame(self, df: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
        drop = {
            f.name
            for f in spec.features
            if f.role in {FeatureRole.ID, FeatureRole.TIME}
        }
        drop.add("timestamp")
        if spec.target is not None:
            drop.add(spec.target.name)
        cols = [c for c in df.columns if c not in drop]
        x = df[cols].copy()
        # Simple encoding: one-hot categoricals, median-impute numerics.
        x = pd.get_dummies(x, dummy_na=False)
        x = x.fillna(x.median(numeric_only=True))
        x = x.fillna(0)
        return x

    def _evaluate(self, df: pd.DataFrame, spec: DatasetSpec) -> EvaluationReport:
        if spec.task_type == TaskType.CLUSTERING:
            return self._evaluate_clustering(df, spec)
        if spec.target is None or spec.target.name not in df.columns:
            return EvaluationReport(
                task_type=spec.task_type.value,
                baseline_model="none",
                notes=["no target to evaluate"],
            )
        if spec.task_type.is_regression or spec.task_type == TaskType.TIME_SERIES:
            return self._evaluate_regression(df, spec)
        return self._evaluate_classification(df, spec)

    def _evaluate_classification(
        self, df: pd.DataFrame, spec: DatasetSpec
    ) -> EvaluationReport:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )
        from sklearn.model_selection import train_test_split

        x = self._feature_frame(df, spec)
        y = df[spec.target.name]
        stratify = y if y.value_counts().min() >= 2 else None
        x_tr, x_te, y_tr, y_te = train_test_split(
            x, y, test_size=0.25, random_state=spec.random_seed, stratify=stratify
        )
        model = RandomForestClassifier(
            n_estimators=120, random_state=spec.random_seed, n_jobs=-1
        )
        model.fit(x_tr, y_tr)
        pred = model.predict(x_te)

        avg = "binary" if y.nunique() == 2 else "macro"
        pos_label = self._positive_label(y)
        metrics = {
            "accuracy": round(float(accuracy_score(y_te, pred)), 4),
            "precision": round(
                float(precision_score(y_te, pred, average=avg, pos_label=pos_label, zero_division=0)), 4
            ),
            "recall": round(
                float(recall_score(y_te, pred, average=avg, pos_label=pos_label, zero_division=0)), 4
            ),
            "f1": round(
                float(f1_score(y_te, pred, average=avg, pos_label=pos_label, zero_division=0)), 4
            ),
        }
        try:
            if y.nunique() == 2:
                proba = model.predict_proba(x_te)[:, 1]
                metrics["roc_auc"] = round(float(roc_auc_score(y_te, proba)), 4)
        except Exception:
            pass

        # Readiness anchored on how far above random the model gets.
        baseline_acc = float(y.value_counts(normalize=True).max())
        lift = (metrics["accuracy"] - baseline_acc) / max(1e-6, 1 - baseline_acc)
        signal_score = float(np.clip(metrics.get("roc_auc", 0.5) * 2 - 1, 0, 1))
        readiness = self._readiness(df, spec, max(lift, signal_score))
        return EvaluationReport(
            task_type=spec.task_type.value,
            baseline_model="RandomForestClassifier",
            metrics=metrics,
            ml_readiness_score=readiness,
            notes=[f"majority-class baseline accuracy = {round(baseline_acc, 4)}"],
        )

    def _positive_label(self, y: pd.Series):
        if y.dtype == object:
            # Heuristic: treat the minority class as positive.
            return y.value_counts().idxmin()
        return 1

    def _evaluate_regression(
        self, df: pd.DataFrame, spec: DatasetSpec
    ) -> EvaluationReport:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        from sklearn.model_selection import train_test_split

        x = self._feature_frame(df, spec)
        y = df[spec.target.name].astype(float)
        x_tr, x_te, y_tr, y_te = train_test_split(
            x, y, test_size=0.25, random_state=spec.random_seed
        )
        model = RandomForestRegressor(
            n_estimators=120, random_state=spec.random_seed, n_jobs=-1
        )
        model.fit(x_tr, y_tr)
        pred = model.predict(x_te)
        r2 = float(r2_score(y_te, pred))
        metrics = {
            "r2": round(r2, 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_te, pred))), 4),
            "mae": round(float(mean_absolute_error(y_te, pred)), 4),
        }
        readiness = self._readiness(df, spec, float(np.clip(r2, 0, 1)))
        return EvaluationReport(
            task_type=spec.task_type.value,
            baseline_model="RandomForestRegressor",
            metrics=metrics,
            ml_readiness_score=readiness,
        )

    def _evaluate_clustering(
        self, df: pd.DataFrame, spec: DatasetSpec
    ) -> EvaluationReport:
        from sklearn.metrics import silhouette_score
        from sklearn.preprocessing import StandardScaler

        x = self._feature_frame(df, spec)
        if spec.target is not None and spec.target.name in df.columns:
            labels = df[spec.target.name]
        else:
            return EvaluationReport(
                task_type=spec.task_type.value,
                baseline_model="none",
                notes=["no cluster labels"],
            )
        xs = StandardScaler().fit_transform(x.select_dtypes(include=[np.number]))
        sample = min(len(xs), 5000)
        idx = np.random.default_rng(spec.random_seed).choice(len(xs), sample, replace=False)
        score = float(silhouette_score(xs[idx], labels.iloc[idx]))
        metrics = {"silhouette": round(score, 4), "n_clusters": int(labels.nunique())}
        readiness = self._readiness(df, spec, float(np.clip((score + 1) / 2, 0, 1)))
        return EvaluationReport(
            task_type=spec.task_type.value,
            baseline_model="KMeans+silhouette",
            metrics=metrics,
            ml_readiness_score=readiness,
        )

    def _readiness(self, df: pd.DataFrame, spec: DatasetSpec, signal: float) -> float:
        """Composite 0-100 score: learnable signal + data completeness."""

        completeness = 1.0 - float(df.isna().mean().mean())
        dup_penalty = float(df.duplicated().mean())
        n_features = len([f for f in spec.features if f.role == FeatureRole.FEATURE])
        breadth = float(np.clip(n_features / 10.0, 0.3, 1.0))
        score = 100.0 * (
            0.6 * signal + 0.25 * completeness + 0.15 * breadth
        ) * (1 - 0.5 * dup_penalty)
        return round(float(np.clip(score, 0, 100)), 1)
