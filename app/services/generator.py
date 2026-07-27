"""High-level facade over the pipeline.

Most callers (CLI, API, notebooks) only need these two entry points.
"""

from __future__ import annotations

from pathlib import Path

from app.graph.orchestrator import DatasetPipeline, PipelineOptions
from app.models.artifacts import GenerationResult
from app.models.spec import DatasetSpec


class DatasetService:
    def __init__(self) -> None:
        self.pipeline = DatasetPipeline()

    def plan(self, prompt: str) -> DatasetSpec:
        """Return the plan without generating data (human-in-the-loop review)."""

        return self.pipeline.plan(prompt)

    def generate_from_prompt(
        self,
        prompt: str,
        *,
        rows: int | None = None,
        seed: int | None = None,
        formats: list[str] | None = None,
        out_dir: str | Path | None = None,
        full: bool = True,
    ) -> GenerationResult:
        spec = self.pipeline.plan(prompt)
        if rows is not None:
            spec.n_rows = rows
        if seed is not None:
            spec.random_seed = seed
        return self.generate_from_spec(
            spec, formats=formats, out_dir=out_dir, full=full
        )

    def generate_from_spec(
        self,
        spec: DatasetSpec,
        *,
        formats: list[str] | None = None,
        out_dir: str | Path | None = None,
        full: bool = True,
    ) -> GenerationResult:
        options = PipelineOptions(
            validate=full,
            run_eda=full,
            evaluate=full,
            document=full,
            export_formats=tuple(formats or ["csv"]),
            out_dir=Path(out_dir) if out_dir else None,
        )
        return self.pipeline.generate(spec, options)
