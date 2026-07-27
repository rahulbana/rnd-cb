from app.agents.planner import HeuristicPlanner
from app.models.spec import TaskType


def test_fraud_prompt_infers_binary_classification_and_rate():
    spec = HeuristicPlanner().plan(
        "Create a fraud detection dataset with 500,000 records, "
        "25 numerical features, 10 categorical features, 2% fraud rate."
    )
    assert spec.task_type == TaskType.BINARY_CLASSIFICATION
    assert spec.n_rows == 500_000
    assert spec.target is not None
    assert abs(spec.target.positive_rate - 0.02) < 1e-9
    assert spec.domain == "banking"


def test_churn_prompt_parses_rows_and_rate():
    spec = HeuristicPlanner().plan(
        "Generate a telecom churn dataset with 250,000 customers and 12% churn."
    )
    assert spec.task_type == TaskType.BINARY_CLASSIFICATION
    assert spec.n_rows == 250_000
    assert abs(spec.target.positive_rate - 0.12) < 1e-9


def test_house_price_prompt_is_regression():
    spec = HeuristicPlanner().plan(
        "Create a regression dataset for predicting house prices using 30 features."
    )
    assert spec.task_type == TaskType.REGRESSION
    assert spec.target is not None


def test_clustering_prompt():
    spec = HeuristicPlanner().plan(
        "Build a customer segmentation dataset for clustering with 10000 rows."
    )
    assert spec.task_type == TaskType.CLUSTERING
    assert spec.n_rows == 10000


def test_generic_prompt_feature_counts():
    spec = HeuristicPlanner().plan(
        "Generate a classification dataset with 6 numerical features and "
        "4 categorical features."
    )
    numeric = [f for f in spec.features if f.dtype.value in {"float", "integer"}
               and f.role.value == "feature"]
    categorical = [f for f in spec.features if f.dtype.value == "category"]
    assert len(numeric) == 6
    assert len(categorical) == 4


def test_quality_signals_detected():
    spec = HeuristicPlanner().plan(
        "Generate a noisy dataset with missing values, duplicates and outliers."
    )
    assert spec.quality.missing_rate > 0
    assert spec.quality.duplicate_rate > 0
    assert spec.quality.outlier_rate > 0
    assert spec.quality.noise > 0


def test_million_shorthand():
    spec = HeuristicPlanner().plan("Create a dataset with 1.5 million rows.")
    assert spec.n_rows == 1_500_000
