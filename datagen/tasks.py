"""Synthetic feature/target generators for ML tasks.

These build numeric feature matrices with a genuine relationship to the target
(NumPy only — no scikit-learn dependency), so generated datasets are actually
learnable:

* :func:`make_classification` – class-conditional Gaussian clusters.
* :func:`make_regression` – linear target plus Gaussian noise.
* :func:`make_clustering` – Gaussian blobs around random centers.

Each returns a :class:`pandas.DataFrame` of features plus a target column.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .spec import DatasetSpec


def _feature_names(n: int) -> list[str]:
    return [f"feature_{i}" for i in range(n)]


def make_classification(spec: DatasetSpec, rng: np.random.Generator) -> pd.DataFrame:
    n, d, k = spec.n_rows, spec.n_features, spec.n_classes
    # One Gaussian cluster per class, centers spread on a hypercube.
    centers = rng.uniform(-5.0, 5.0, size=(k, d))
    labels = rng.integers(0, k, size=n)
    noise = rng.normal(0.0, spec.cluster_std, size=(n, d))
    features = centers[labels] + noise

    names = _feature_names(d)
    df = pd.DataFrame(features, columns=names).round(4)
    if spec.class_names:
        mapping = {i: name for i, name in enumerate(spec.class_names)}
        df[spec.target_name] = [mapping[int(l)] for l in labels]
    else:
        df[spec.target_name] = labels.astype("int64")
    return df


def make_regression(spec: DatasetSpec, rng: np.random.Generator) -> pd.DataFrame:
    n, d = spec.n_rows, spec.n_features
    n_informative = spec.n_informative if spec.n_informative is not None else d
    n_informative = min(max(1, n_informative), d)

    features = rng.normal(0.0, 1.0, size=(n, d))
    coef = np.zeros(d)
    informative = rng.choice(d, size=n_informative, replace=False)
    coef[informative] = rng.uniform(-10.0, 10.0, size=n_informative)
    target = features @ coef + rng.normal(0.0, spec.noise, size=n)

    names = _feature_names(d)
    df = pd.DataFrame(features, columns=names).round(4)
    df[spec.target_name] = np.round(target, 4)
    return df


def make_clustering(spec: DatasetSpec, rng: np.random.Generator) -> pd.DataFrame:
    n, d, k = spec.n_rows, spec.n_features, spec.n_clusters
    centers = rng.uniform(-10.0, 10.0, size=(k, d))
    assignments = rng.integers(0, k, size=n)
    noise = rng.normal(0.0, spec.cluster_std, size=(n, d))
    features = centers[assignments] + noise

    names = _feature_names(d)
    df = pd.DataFrame(features, columns=names).round(4)
    # Ground-truth cluster id is provided as a convenience for evaluation.
    df[spec.target_name] = assignments.astype("int64")
    return df
