import pandas as pd

from app.graph.orchestrator import DatasetPipeline, PipelineOptions
from app.services.generator import DatasetService


def test_end_to_end_classification(tmp_path):
    pipeline = DatasetPipeline()
    result = pipeline.run(
        "Create a fraud detection dataset with 3000 records and 3% fraud rate.",
        PipelineOptions(export_formats=("csv", "json"), out_dir=tmp_path),
    )
    assert len(result.data) >= 3000
    assert result.validation is not None and result.validation.passed
    assert result.evaluation is not None
    # A learnable dataset should score above a trivial baseline.
    assert result.evaluation.ml_readiness_score > 30
    assert "roc_auc" in result.evaluation.metrics
    # Files were written into a per-dataset subdirectory.
    from pathlib import Path

    assert result.output_dir == str(tmp_path / result.spec.name)
    assert (tmp_path / result.spec.name / f"{result.spec.name}.csv").exists()
    assert (tmp_path / result.spec.name / f"{result.spec.name}.json").exists()
    # Nothing is written loosely into the parent directory.
    assert not any(p.is_file() for p in tmp_path.iterdir())
    assert Path(result.exports["csv"]).parent == tmp_path / result.spec.name


def test_end_to_end_regression(tmp_path):
    result = DatasetPipeline().run(
        "Create a regression dataset for predicting house prices with 2500 rows.",
        PipelineOptions(export_formats=("csv",), out_dir=tmp_path),
    )
    assert result.spec.task_type.value == "regression"
    assert "r2" in result.evaluation.metrics
    assert result.eda["shape"]["rows"] == len(result.data)


def test_service_full_run(tmp_path):
    service = DatasetService()
    result = service.generate_from_prompt(
        "Generate a telecom churn dataset with 2000 customers and 15% churn.",
        formats=["csv", "sqlite", "sql"],
        out_dir=tmp_path,
    )
    summary = result.summary()
    assert summary["task_type"] == "binary_classification"
    assert set(["csv", "sqlite", "sql"]).issubset(result.exports.keys())
    # Data dictionary covers every column.
    assert len(result.data_dictionary) == result.data.shape[1]
    # SQL DDL is a CREATE TABLE statement.
    from pathlib import Path

    ddl = Path(result.exports["sql"]).read_text()
    assert ddl.startswith("CREATE TABLE")


def test_eda_notebook_is_written(tmp_path):
    import json

    result = DatasetService().generate_from_prompt(
        "Create a fraud detection dataset with 1200 rows and 3% fraud rate.",
        formats=["csv"],
        out_dir=tmp_path,
    )
    # A notebook is produced instead of a static eda.json.
    assert "eda_notebook" in result.exports
    assert "eda" not in result.exports
    nb_path = tmp_path / result.spec.name / f"{result.spec.name}_eda.ipynb"
    assert nb_path.exists()

    nb = json.loads(nb_path.read_text())
    assert nb["nbformat"] == 4
    assert len(nb["cells"]) > 5
    # Every cell has an id (nbformat >= 4.5 requirement).
    assert all(c.get("id") for c in nb["cells"])
    assert any(c["cell_type"] == "code" for c in nb["cells"])
    # The loader references the exported CSV so the notebook is runnable.
    source = "\n".join(
        c["source"] for c in nb["cells"] if c["cell_type"] == "code"
    )
    assert f"{result.spec.name}.csv" in source


def test_exports_readable(tmp_path):
    result = DatasetService().generate_from_prompt(
        "Create a customer segmentation dataset with 1500 rows.",
        formats=["csv", "parquet"],
        out_dir=tmp_path,
        full=False,
    )
    csv = pd.read_csv(result.exports["csv"])
    parquet = pd.read_parquet(result.exports["parquet"])
    assert len(csv) == len(parquet) == len(result.data)


def test_plan_only_does_not_generate():
    spec = DatasetService().plan("fraud dataset with 1% fraud rate")
    assert spec.target.positive_rate == 0.01
    assert spec.n_rows > 0


def test_end_to_end_clustering(tmp_path):
    result = DatasetPipeline().run(
        "Create a customer segmentation dataset with 2000 rows for clustering.",
        PipelineOptions(export_formats=("csv",), out_dir=tmp_path),
    )
    assert result.spec.task_type.value == "clustering"
    assert result.eda["target"]["type"] == "clustering"
    assert "silhouette" in result.evaluation.metrics


def test_end_to_end_time_series(tmp_path):
    result = DatasetPipeline().run(
        "Generate a manufacturing sensor time-series dataset with 1500 rows and anomalies.",
        PipelineOptions(export_formats=("csv",), out_dir=tmp_path),
    )
    assert result.spec.task_type.value == "time_series"
    assert "timestamp" in result.data.columns
    assert result.eda["target"]["type"] == "regression"
