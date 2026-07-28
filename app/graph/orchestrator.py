"""Pipeline orchestration.

The design specifies a LangGraph-style DAG of agents. To keep the platform
runnable with zero heavy dependencies (and trivially testable), the reference
orchestrator is a plain, explicit pipeline that wires the same agents in the
same order:

    plan -> schema -> features -> correlations -> target -> quality
         -> validation -> eda -> evaluation -> documentation -> export

Each stage is toggleable so callers can run a fast "generate only" pass or the
full analytical suite. A drop-in LangGraph implementation can wrap these same
agent objects without changing them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.agents import (
    CorrelationAgent,
    DocumentationAgent,
    EDAAgent,
    EvaluationAgent,
    ExportAgent,
    FeatureAgent,
    QualityAgent,
    SchemaAgent,
    TargetAgent,
    ValidationAgent,
    get_planner,
)
from app.config import settings
from app.models.artifacts import GenerationResult
from app.models.spec import DatasetSpec
from app.utils.rng import make_rng

import logging

logger = logging.getLogger("dataset_agent")


@dataclass
class PipelineOptions:
    validate: bool = True
    run_eda: bool = True
    evaluate: bool = True
    document: bool = True
    export_formats: tuple[str, ...] = ("csv",)
    write_reports: bool = True
    out_dir: Path | None = None


class DatasetPipeline:
    """Runs the full agent pipeline end to end."""

    def __init__(self) -> None:
        self.planner = get_planner()
        self.schema = SchemaAgent()
        self.feature = FeatureAgent()
        self.correlation = CorrelationAgent()
        self.target = TargetAgent()
        self.quality = QualityAgent()
        self.validation = ValidationAgent()
        self.eda = EDAAgent()
        self.evaluation = EvaluationAgent()
        self.documentation = DocumentationAgent()
        self.exporter = ExportAgent()

    def plan(self, prompt: str) -> DatasetSpec:
        return self.planner.plan(prompt)

    def generate(
        self, spec: DatasetSpec, options: PipelineOptions | None = None
    ) -> GenerationResult:
        options = options or PipelineOptions()
        rng = make_rng(spec.random_seed)

        step = 0

        def stage(label: str) -> None:
            nonlocal step
            step += 1
            logger.info("▶ Step %d — %s", step, label)

        logger.info(
            "=== Generating '%s' (%s, %d rows, seed=%d) ===",
            spec.name, spec.task_type.value, spec.n_rows, spec.random_seed,
        )

        stage("Schema: finalise columns, keys, and types")
        spec = self.schema.run(spec)
        stage("Features: draw each column from its distribution")
        df = self.feature.run(spec, rng)
        stage("Correlations: impose feature dependencies")
        df = self.correlation.run(df, spec, rng)
        stage("Target: synthesise the label from the features")
        df = self.target.run(df, spec, rng)
        stage("Quality: inject missing/duplicates/outliers/noise")
        df = self.quality.run(df, spec, rng)

        result = GenerationResult(spec=spec, data=df)

        if options.validate:
            stage("Validation: structural & statistical checks")
            result.validation = self.validation.run(df, spec)
        if options.run_eda:
            stage("EDA: compute summaries, correlations, target distribution")
            result.eda = self.eda.run(df, spec)
        if options.evaluate:
            stage("Evaluation: train baseline model, score ML-readiness")
            result.evaluation = self.evaluation.run(df, spec)
        if options.document:
            stage("Documentation: build the data dictionary")
            self.documentation.run(result)

        if options.export_formats:
            stage(f"Export: write {', '.join(options.export_formats)} + reports")
            # Each run gets its own subdirectory so a dataset's files (data,
            # notebook, card, schema, dictionary) stay grouped together instead
            # of accumulating loosely in the shared datasets/ directory.
            base_dir = Path(options.out_dir or settings.datasets_dir)
            out_dir = base_dir / spec.name
            result.output_dir = str(out_dir)
            result.exports = self.exporter.run(
                df, spec, out_dir, list(options.export_formats)
            )
            if options.write_reports:
                self._write_reports(result, out_dir)
            logger.info("✓ Done — %d rows written to %s", len(df), out_dir)

        return result

    def run(
        self, prompt: str, options: PipelineOptions | None = None
    ) -> GenerationResult:
        """Convenience: plan from a prompt, then generate."""

        spec = self.plan(prompt)
        return self.generate(spec, options)

    def _write_reports(self, result: GenerationResult, out_dir: Path) -> None:
        if result.data_dictionary:
            result.exports["data_dictionary"] = self.exporter.write_json(
                out_dir, f"{result.spec.name}_data_dictionary.json",
                result.data_dictionary,
            )
        if result.eda:
            result.exports["eda_notebook"] = self._write_eda_notebook(result, out_dir)
        card = self.documentation.dataset_card(result)
        result.exports["dataset_card"] = self.exporter.write_text(
            out_dir, f"{result.spec.name}_CARD.md", card
        )
        result.exports["json_schema"] = self.exporter.write_json(
            out_dir, f"{result.spec.name}_schema.json",
            self.documentation.json_schema(result.spec),
        )

    def _write_eda_notebook(self, result: GenerationResult, out_dir: Path) -> str:
        """Emit a runnable EDA notebook that loads an exported data file."""

        from app.utils.notebook import build_eda_notebook

        # Reference the first available on-disk data export (csv > parquet > json).
        data_filename = f"{result.spec.name}.csv"
        for fmt in ("csv", "parquet", "json"):
            if fmt in result.exports:
                data_filename = Path(result.exports[fmt]).name
                break
        readiness = (
            result.evaluation.ml_readiness_score if result.evaluation else None
        )
        notebook = build_eda_notebook(
            result.spec, result.eda, data_filename, readiness
        )
        return self.exporter.write_notebook(
            out_dir, f"{result.spec.name}_eda.ipynb", notebook
        )
