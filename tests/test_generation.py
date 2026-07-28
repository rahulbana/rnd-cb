import numpy as np
import pandas as pd

from app.agents import (
    CorrelationAgent,
    FeatureAgent,
    QualityAgent,
    SchemaAgent,
    TargetAgent,
    ValidationAgent,
)
from app.models.spec import (
    CorrelationSpec,
    DatasetSpec,
    Distribution,
    DType,
    FeatureSpec,
    QualitySpec,
    TargetSpec,
    TaskType,
)
from app.utils.rng import make_rng


def _base_spec(**kwargs) -> DatasetSpec:
    spec = DatasetSpec(
        name="test",
        task_type=TaskType.BINARY_CLASSIFICATION,
        n_rows=2000,
        features=[
            FeatureSpec(name="a", dtype=DType.FLOAT, distribution=Distribution.NORMAL),
            FeatureSpec(name="b", dtype=DType.FLOAT, distribution=Distribution.GAMMA,
                        params={"shape": 2.0, "scale": 2.0}),
            FeatureSpec(name="c", dtype=DType.CATEGORY,
                        categories=["x", "y", "z"]),
        ],
        target=TargetSpec(name="label", positive_rate=0.2),
        **kwargs,
    )
    return SchemaAgent().run(spec)


def test_feature_agent_shapes_and_id():
    spec = _base_spec()
    rng = make_rng(spec.random_seed)
    df = FeatureAgent().run(spec, rng)
    assert len(df) == 2000
    assert "id" in df.columns
    assert df["id"].is_unique
    assert set(["a", "b", "c"]).issubset(df.columns)


def test_reproducible_with_same_seed():
    spec = _base_spec()
    df1 = FeatureAgent().run(spec, make_rng(spec.random_seed))
    df2 = FeatureAgent().run(spec, make_rng(spec.random_seed))
    pd.testing.assert_frame_equal(df1, df2)


def test_target_respects_positive_rate():
    spec = _base_spec()
    rng = make_rng(spec.random_seed)
    df = FeatureAgent().run(spec, rng)
    df = TargetAgent().run(df, spec, rng)
    rate = df["label"].mean()
    assert 0.15 < rate < 0.25  # close to requested 0.2


def test_target_is_learnable():
    """A high signal_strength should make the label correlated with features."""

    spec = _base_spec()
    spec.target.signal_strength = 0.95
    rng = make_rng(spec.random_seed)
    df = FeatureAgent().run(spec, rng)
    df = TargetAgent().run(df, spec, rng)
    # At least one numeric feature should differ across classes.
    means = df.groupby("label")["a"].mean()
    assert abs(means.iloc[0] - means.iloc[1]) > 0.05


def test_correlation_agent_induces_correlation():
    spec = _base_spec()
    spec.correlations = [CorrelationSpec(source="a", target="b", strength=0.8)]
    rng = make_rng(spec.random_seed)
    df = FeatureAgent().run(spec, rng)
    df = CorrelationAgent().run(df, spec, rng)
    corr = np.corrcoef(df["a"], df["b"])[0, 1]
    assert corr > 0.6


def test_quality_injects_missing_and_duplicates():
    spec = _base_spec()
    spec.quality = QualitySpec(missing_rate=0.1, duplicate_rate=0.05, outlier_rate=0.02)
    rng = make_rng(spec.random_seed)
    df = FeatureAgent().run(spec, rng)
    df = TargetAgent().run(df, spec, rng)
    n_before = len(df)
    df = QualityAgent().run(df, spec, rng)
    assert df.isna().sum().sum() > 0
    assert len(df) > n_before  # duplicates added
    # Target must remain intact (never nulled).
    assert not df["label"].isna().any()


def test_quality_injection_on_boolean_and_integer_columns():
    """Regression: pandas 3 rejects NaN/float set into bool/int columns.

    Quality injection must upcast instead of raising.
    """

    spec = DatasetSpec(
        name="mixed",
        task_type=TaskType.BINARY_CLASSIFICATION,
        n_rows=1500,
        features=[
            FeatureSpec(name="count", dtype=DType.INTEGER,
                        distribution=Distribution.POISSON, params={"lam": 4}),
            FeatureSpec(name="flag_a", dtype=DType.BOOLEAN),
            FeatureSpec(name="flag_b", dtype=DType.BOOLEAN),
            FeatureSpec(name="amount", dtype=DType.FLOAT),
        ],
        target=TargetSpec(name="label", positive_rate=0.2),
        quality=QualitySpec(missing_rate=0.08, outlier_rate=0.03, noise=0.0),
    )
    spec = SchemaAgent().run(spec)
    rng = make_rng(spec.random_seed)
    df = FeatureAgent().run(spec, rng)
    df = TargetAgent().run(df, spec, rng)
    # Must not raise on bool/int columns.
    df = QualityAgent().run(df, spec, rng)
    # Missing values landed in both a boolean and an integer column.
    assert df["flag_a"].isna().any()
    assert df["count"].isna().any()
    # Target stays intact.
    assert not df["label"].isna().any()


def test_multiclass_target():
    spec = DatasetSpec(
        name="mc",
        task_type=TaskType.MULTICLASS_CLASSIFICATION,
        n_rows=1500,
        features=[
            FeatureSpec(name="a", dtype=DType.FLOAT),
            FeatureSpec(name="b", dtype=DType.FLOAT),
        ],
        target=TargetSpec(name="y", n_classes=4),
    )
    spec = SchemaAgent().run(spec)
    rng = make_rng(spec.random_seed)
    df = FeatureAgent().run(spec, rng)
    df = TargetAgent().run(df, spec, rng)
    assert df["y"].nunique() >= 3


def test_validation_passes_on_clean_spec():
    spec = _base_spec()
    rng = make_rng(spec.random_seed)
    df = FeatureAgent().run(spec, rng)
    df = TargetAgent().run(df, spec, rng)
    report = ValidationAgent().run(df, spec)
    assert report.passed, report.failures
