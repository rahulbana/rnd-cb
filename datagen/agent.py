"""High-level data generation agent.

:class:`DataGenAgent` is the single entry point most users need.  Give it a
spec (dict, :class:`~datagen.spec.DatasetSpec`, or JSON/YAML file) and it
returns a ready-to-use :class:`pandas.DataFrame`, or writes it straight to
disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import tasks, text
from .columns import generate_column
from .outliers import inject_outliers
from .spec import ColumnSpec, DatasetSpec


class DataGenAgent:
    """Generate synthetic datasets from a declarative spec."""

    def __init__(self, spec: DatasetSpec | dict[str, Any]):
        if isinstance(spec, dict):
            spec = DatasetSpec.from_dict(spec)
        self.spec = spec
        self.rng = np.random.default_rng(spec.seed)

    # -- construction helpers ------------------------------------------------

    @classmethod
    def from_file(cls, path: str | Path) -> "DataGenAgent":
        """Load a spec from a ``.json``, ``.yaml`` or ``.yml`` file."""
        path = Path(path)
        raw = path.read_text()
        if path.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml  # type: ignore
            except ModuleNotFoundError as exc:  # pragma: no cover
                raise RuntimeError(
                    "PyYAML is required to load YAML specs (pip install pyyaml)."
                ) from exc
            data = yaml.safe_load(raw)
        else:
            data = json.loads(raw)
        return cls(DatasetSpec.from_dict(data))

    # -- generation ----------------------------------------------------------

    def generate(self) -> pd.DataFrame:
        """Generate the dataset described by the spec."""
        task = self.spec.task
        if task == "tabular":
            return self._generate_tabular()
        if task in {"classification", "regression", "clustering"}:
            return self._generate_ml_task()
        if task == "text_classification":
            return self._generate_text_classification()
        if task == "summarization":
            return self._generate_summarization()
        raise ValueError(f"Unsupported task '{task}'.")  # pragma: no cover

    def _generate_columns(self) -> pd.DataFrame:
        data = {
            col.name: generate_column(col, self.rng, self.spec.n_rows)
            for col in self.spec.columns
        }
        return pd.DataFrame(data)

    def _generate_tabular(self) -> pd.DataFrame:
        if not self.spec.columns:
            raise ValueError("tabular task requires at least one column spec.")
        return self._generate_columns()

    def _apply_feature_outliers(self, df: pd.DataFrame, feature_cols: list[str]) -> None:
        pct = self.spec.feature_outlier_pct
        if pct <= 0:
            return
        for name in feature_cols:
            faux = ColumnSpec(name=name, dtype="float", outlier_pct=pct, decimals=4)
            df[name] = inject_outliers(df[name].to_numpy(dtype=object), faux, self.rng)

    def _generate_ml_task(self) -> pd.DataFrame:
        builders = {
            "classification": tasks.make_classification,
            "regression": tasks.make_regression,
            "clustering": tasks.make_clustering,
        }
        df = builders[self.spec.task](self.spec, self.rng)
        feature_cols = [c for c in df.columns if c != self.spec.target_name]
        self._apply_feature_outliers(df, feature_cols)

        # Append any extra user-specified columns alongside the synthetic ones.
        if self.spec.columns:
            extra = self._generate_columns()
            target = df.pop(self.spec.target_name)
            df = pd.concat([df, extra], axis=1)
            df[self.spec.target_name] = target
        return df

    def _generate_text_classification(self) -> pd.DataFrame:
        cfg = self.spec.text
        return text.generate_text_classification(
            self.rng,
            self.spec.n_rows,
            labels=cfg.get("labels"),
            flavor=cfg.get("flavor", "topic"),
            words=tuple(cfg.get("words", (12, 40))),
            target_name=cfg.get("target_name", self.spec.target_name if self.spec.target_name != "target" else "label"),
        )

    def _generate_summarization(self) -> pd.DataFrame:
        cfg = self.spec.text
        return text.generate_summarization(
            self.rng,
            self.spec.n_rows,
            sentences_per_doc=tuple(cfg.get("sentences_per_doc", (4, 8))),
            words=tuple(cfg.get("words", (10, 20))),
        )

    # -- output --------------------------------------------------------------

    def to_file(self, path: str | Path, fmt: str | None = None) -> Path:
        """Generate and write the dataset. Format inferred from extension."""
        path = Path(path)
        fmt = (fmt or path.suffix.lstrip(".") or "csv").lower()
        df = self.generate()
        if fmt == "csv":
            df.to_csv(path, index=False)
        elif fmt in {"json"}:
            df.to_json(path, orient="records", indent=2)
        elif fmt in {"jsonl", "ndjson"}:
            df.to_json(path, orient="records", lines=True)
        elif fmt in {"parquet", "pq"}:
            df.to_parquet(path, index=False)
        else:
            raise ValueError(f"Unsupported output format '{fmt}'.")
        return path


def generate(spec: DatasetSpec | dict[str, Any]) -> pd.DataFrame:
    """Convenience one-liner: ``generate(spec_dict)`` -> DataFrame."""
    return DataGenAgent(spec).generate()
