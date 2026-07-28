"""Export agent: write the dataset and its docs to disk in many formats.

Supported: csv, parquet, json, excel, sqlite, and a portable SQL ``CREATE TABLE``
schema. Each ``export_*`` returns the path written so callers can surface links.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from app.agents.base import Agent
from app.models.spec import DatasetSpec, DType, FeatureRole

# Logical dtype -> ANSI-ish SQL type for the generated DDL.
_SQL_TYPES = {
    DType.INTEGER: "INTEGER",
    DType.FLOAT: "DOUBLE PRECISION",
    DType.BOOLEAN: "BOOLEAN",
    DType.CATEGORY: "VARCHAR(64)",
    DType.ORDINAL: "VARCHAR(64)",
    DType.DATETIME: "TIMESTAMP",
    DType.UUID: "VARCHAR(36)",
    DType.EMAIL: "VARCHAR(255)",
    DType.PHONE: "VARCHAR(32)",
    DType.URL: "VARCHAR(512)",
    DType.NAME: "VARCHAR(128)",
    DType.TEXT: "TEXT",
}


class ExportAgent(Agent):
    name = "exporter"

    def run(
        self,
        df: pd.DataFrame,
        spec: DatasetSpec,
        out_dir: Path,
        formats: list[str],
    ) -> dict[str, str]:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        base = out_dir / spec.name
        written: dict[str, str] = {}

        handlers = {
            "csv": lambda: self._csv(df, base),
            "parquet": lambda: self._parquet(df, base),
            "json": lambda: self._json(df, base),
            "excel": lambda: self._excel(df, base),
            "xlsx": lambda: self._excel(df, base),
            "sqlite": lambda: self._sqlite(df, spec, base),
            "sql": lambda: self._sql_schema(df, spec, base),
        }
        for fmt in formats:
            handler = handlers.get(fmt.lower())
            if handler is None:
                self.log(f"skipping unknown format '{fmt}'")
                continue
            try:
                written[fmt] = str(handler())
            except Exception as exc:  # pragma: no cover - defensive
                self.log(f"export '{fmt}' failed: {exc}")
        self.log(f"exported formats: {list(written)}")
        return written

    def _csv(self, df: pd.DataFrame, base: Path) -> Path:
        path = base.with_suffix(".csv")
        df.to_csv(path, index=False)
        return path

    def _parquet(self, df: pd.DataFrame, base: Path) -> Path:
        path = base.with_suffix(".parquet")
        df.to_parquet(path, index=False)
        return path

    def _json(self, df: pd.DataFrame, base: Path) -> Path:
        path = base.with_suffix(".json")
        df.to_json(path, orient="records", date_format="iso")
        return path

    def _excel(self, df: pd.DataFrame, base: Path) -> Path:
        path = base.with_suffix(".xlsx")
        # Excel caps at ~1M rows; sample if larger.
        frame = df if len(df) <= 1_000_000 else df.head(1_000_000)
        frame.to_excel(path, index=False)
        return path

    def _sqlite(self, df: pd.DataFrame, spec: DatasetSpec, base: Path) -> Path:
        path = base.with_suffix(".sqlite")
        if path.exists():
            path.unlink()
        conn = sqlite3.connect(path)
        try:
            df.to_sql(spec.name, conn, if_exists="replace", index=False)
        finally:
            conn.close()
        return path

    def _sql_schema(self, df: pd.DataFrame, spec: DatasetSpec, base: Path) -> Path:
        path = base.with_suffix(".sql")
        path.write_text(self.build_ddl(df, spec))
        return path

    def build_ddl(self, df: pd.DataFrame, spec: DatasetSpec) -> str:
        spec_by_name = {f.name: f for f in spec.features}
        pk = next(
            (f.name for f in spec.features if f.role == FeatureRole.ID), None
        )
        lines = [f"CREATE TABLE {spec.name} ("]
        col_defs = []
        for col in df.columns:
            feature = spec_by_name.get(col)
            if feature is not None:
                sql_type = _SQL_TYPES.get(feature.dtype, "TEXT")
            else:
                sql_type = self._infer_sql_type(df[col])
            constraint = " PRIMARY KEY" if col == pk else ""
            col_defs.append(f"    {col} {sql_type}{constraint}")
        lines.append(",\n".join(col_defs))
        lines.append(");")
        return "\n".join(lines)

    def _infer_sql_type(self, series: pd.Series) -> str:
        if pd.api.types.is_integer_dtype(series):
            return "INTEGER"
        if pd.api.types.is_float_dtype(series):
            return "DOUBLE PRECISION"
        if pd.api.types.is_bool_dtype(series):
            return "BOOLEAN"
        if pd.api.types.is_datetime64_any_dtype(series):
            return "TIMESTAMP"
        return "TEXT"

    def write_text(self, out_dir: Path, filename: str, content: str) -> str:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        path.write_text(content)
        return str(path)

    def write_json(self, out_dir: Path, filename: str, data) -> str:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        path.write_text(json.dumps(data, indent=2, default=str))
        return str(path)

    def write_notebook(self, out_dir: Path, filename: str, notebook: dict) -> str:
        """Write an nbformat-v4 notebook dict to a ``.ipynb`` file."""

        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        path.write_text(json.dumps(notebook, indent=1))
        return str(path)
