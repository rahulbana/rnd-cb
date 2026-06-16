"""Tests for the datagen agent."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from datagen import DataGenAgent, SpecError, generate
from datagen.outliers import OUTLIER_LABEL


# -- spec validation ---------------------------------------------------------

def test_invalid_dtype_rejected():
    with pytest.raises(SpecError):
        DataGenAgent({"task": "tabular", "n_rows": 5,
                      "columns": [{"name": "x", "dtype": "complex"}]})


def test_outlier_pct_bounds():
    with pytest.raises(SpecError):
        DataGenAgent({"task": "tabular", "n_rows": 5,
                      "columns": [{"name": "x", "dtype": "int", "outlier_pct": 2}]})


def test_unknown_column_key_rejected():
    with pytest.raises(SpecError):
        DataGenAgent({"task": "tabular", "n_rows": 5,
                      "columns": [{"name": "x", "dtype": "int", "bogus": 1}]})


# -- shape and reproducibility ----------------------------------------------

def test_row_and_column_counts():
    df = generate({
        "task": "tabular", "n_rows": 50,
        "columns": [
            {"name": "a", "dtype": "int", "min": 0, "max": 10},
            {"name": "b", "dtype": "float"},
        ],
    })
    assert df.shape == (50, 2)
    assert list(df.columns) == ["a", "b"]


def test_seed_is_reproducible():
    spec = {"task": "regression", "n_rows": 100, "n_features": 4, "seed": 5}
    a = DataGenAgent(spec).generate()
    b = DataGenAgent(spec).generate()
    pd.testing.assert_frame_equal(a, b)


# -- column types ------------------------------------------------------------

def test_int_range_respected():
    df = generate({"task": "tabular", "n_rows": 500,
                   "columns": [{"name": "x", "dtype": "int", "min": 5, "max": 9}]})
    vals = df["x"]
    assert vals.min() >= 5 and vals.max() <= 9
    assert all(float(v).is_integer() for v in vals)


def test_category_values_within_set():
    cats = ["a", "b", "c"]
    df = generate({"task": "tabular", "n_rows": 200,
                   "columns": [{"name": "c", "dtype": "category", "categories": cats}]})
    assert set(df["c"].unique()).issubset(set(cats))


def test_bool_and_datetime():
    df = generate({"task": "tabular", "n_rows": 100, "seed": 1,
                   "columns": [
                       {"name": "flag", "dtype": "bool", "p_true": 0.5},
                       {"name": "d", "dtype": "datetime",
                        "min": "2020-01-01", "max": "2020-12-31",
                        "datetime_format": "%Y-%m-%d"},
                   ]})
    assert set(df["flag"].unique()).issubset({True, False})
    assert df["d"].str.match(r"\d{4}-\d{2}-\d{2}").all()


# -- outliers ----------------------------------------------------------------

def test_numeric_outliers_count():
    n, pct = 1000, 0.1
    df = generate({"task": "tabular", "n_rows": n, "seed": 3,
                   "columns": [{"name": "x", "dtype": "float",
                                "distribution": "normal", "mean": 0, "std": 1,
                                "outlier_pct": pct}]})
    x = df["x"].to_numpy(dtype=float)
    # Outliers are pushed 4-8 std away; count values beyond 3 std.
    extreme = np.sum(np.abs(x - np.median(x)) > 3 * np.std(x[np.abs(x) < 4]))
    assert extreme >= int(n * pct * 0.5)  # at least half land clearly outside


def test_category_outlier_sentinel():
    df = generate({"task": "tabular", "n_rows": 200, "seed": 2,
                   "columns": [{"name": "c", "dtype": "category",
                                "categories": ["a", "b"], "outlier_pct": 0.1}]})
    assert OUTLIER_LABEL in set(df["c"].unique())


def test_uuid_name_email_columns():
    df = generate({"task": "tabular", "n_rows": 30, "seed": 1,
                   "columns": [
                       {"name": "id", "dtype": "uuid"},
                       {"name": "person", "dtype": "name"},
                       {"name": "mail", "dtype": "email"},
                   ]})
    assert df["id"].str.match(r"[0-9a-f]{8}-[0-9a-f]{4}-").all()
    assert df["person"].str.contains(" ").all()
    assert df["mail"].str.contains("@").all()


def test_null_injection():
    df = generate({"task": "tabular", "n_rows": 100, "seed": 8,
                   "columns": [{"name": "x", "dtype": "int", "min": 0, "max": 5,
                                "null_pct": 0.2}]})
    assert df["x"].isna().sum() == 20


# -- ML tasks ----------------------------------------------------------------

def test_classification_target_and_signal():
    df = generate({"task": "classification", "n_rows": 300, "n_features": 4,
                   "n_classes": 3, "cluster_std": 0.5, "seed": 0})
    assert df["target"].nunique() == 3
    feature_cols = [c for c in df.columns if c.startswith("feature_")]
    assert len(feature_cols) == 4
    # Class means should differ -> recoverable signal.
    means = df.groupby("target")[feature_cols[0]].mean()
    assert means.max() - means.min() > 1.0


def test_regression_target_is_numeric():
    df = generate({"task": "regression", "n_rows": 200, "n_features": 5,
                   "n_informative": 2, "seed": 4})
    assert pd.api.types.is_numeric_dtype(df["target"])
    assert df.shape == (200, 6)


def test_clustering_ground_truth():
    df = generate({"task": "clustering", "n_rows": 150, "n_features": 2,
                   "n_clusters": 5, "seed": 6})
    assert df["target"].nunique() <= 5


def test_class_names_applied():
    df = generate({"task": "classification", "n_rows": 100, "n_classes": 2,
                   "class_names": ["no", "yes"], "seed": 1})
    assert set(df["target"].unique()).issubset({"no", "yes"})


def test_ml_task_with_extra_columns():
    df = generate({"task": "classification", "n_rows": 80, "n_features": 3,
                   "n_classes": 2, "seed": 1,
                   "columns": [{"name": "region", "dtype": "category",
                                "categories": ["x", "y"]}]})
    assert "region" in df.columns
    assert list(df.columns)[-1] == "target"  # target stays last


# -- text tasks --------------------------------------------------------------

def test_text_classification_signal():
    df = generate({"task": "text_classification", "n_rows": 200, "seed": 1,
                   "text": {"labels": ["finance", "sports"]}})
    assert set(df.columns) == {"text", "label"}
    assert set(df["label"].unique()).issubset({"finance", "sports"})
    # Finance docs should mention finance words more than sports docs.
    fin = df[df["label"] == "finance"]["text"].str.contains("market|stock|profit").mean()
    spo = df[df["label"] == "sports"]["text"].str.contains("market|stock|profit").mean()
    assert fin > spo


def test_summarization_pairs():
    df = generate({"task": "summarization", "n_rows": 50, "seed": 1})
    assert set(df.columns) == {"document", "summary"}
    assert (df["document"].str.len() > df["summary"].str.len()).mean() > 0.9


# -- output ------------------------------------------------------------------

def test_to_file_csv(tmp_path):
    agent = DataGenAgent({"task": "regression", "n_rows": 20, "seed": 1})
    out = agent.to_file(tmp_path / "out.csv")
    assert out.exists()
    reloaded = pd.read_csv(out)
    assert len(reloaded) == 20


def test_to_file_jsonl(tmp_path):
    agent = DataGenAgent({"task": "text_classification", "n_rows": 10, "seed": 1})
    out = agent.to_file(tmp_path / "out.jsonl")
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 10
