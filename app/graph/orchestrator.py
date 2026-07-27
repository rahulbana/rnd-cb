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

        spec = self.schema.run(spec)
        df = self.feature.run(spec, rng)
        df = self.correlation.run(df, spec, rng)
        df = self.target.run(df, spec, rng)
        df = self.quality.run(df, spec, rng)

        result = GenerationResult(spec=spec, data=df)

        if options.validate:
            result.validation = self.validation.run(df, spec)
        if options.run_eda:
            result.eda = self.eda.run(df, spec)
        if options.evaluate:
            result.evaluation = self.evaluation.run(df, spec)
        if options.document:
            self.documentation.run(result)

        if options.export_formats:
            out_dir = options.out_dir or settings.datasets_dir
            result.exports = self.exporter.run(
                df, spec, out_dir, list(options.export_formats)
            )
            if options.write_reports:
                self._write_reports(result, out_dir)

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
            result.exports["eda"] = self.exporter.write_json(
                out_dir, f"{result.spec.name}_eda.json", result.eda
            )
        card = self.documentation.dataset_card(result)
        result.exports["dataset_card"] = self.exporter.write_text(
            out_dir, f"{result.spec.name}_CARD.md", card
        )
        result.exports["json_schema"] = self.exporter.write_json(
            out_dir, f"{result.spec.name}_schema.json",
            self.documentation.json_schema(result.spec),
        )
