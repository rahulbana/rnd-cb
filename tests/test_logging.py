import logging

from app.graph.orchestrator import DatasetPipeline, PipelineOptions
from app.utils.logging import configure_logging


def test_configure_logging_sets_level():
    lg = configure_logging(verbose=True)
    assert lg.level == logging.INFO
    lg = configure_logging(verbose=False)
    assert lg.level == logging.WARNING
    # Restore propagation so this doesn't affect caplog-based tests.
    lg.propagate = True


def test_pipeline_emits_step_by_step_logs(caplog, tmp_path):
    logging.getLogger("dataset_agent").propagate = True
    caplog.set_level(logging.INFO, logger="dataset_agent")

    DatasetPipeline().run(
        "Create a fraud detection dataset with 600 rows and 3% fraud rate.",
        PipelineOptions(export_formats=("csv",), out_dir=tmp_path),
    )

    text = "\n".join(caplog.messages)
    # A numbered banner is emitted for the major stages...
    assert "Step 1 — Schema" in text
    assert "Target" in text
    assert "Export" in text
    # ...and the run reports completion.
    assert any("Done" in m for m in caplog.messages)
