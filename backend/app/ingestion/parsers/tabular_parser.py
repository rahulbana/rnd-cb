"""CSV and Excel parsers.

Tabular data is emitted as one ``ROW`` element per record, each linearized as
``col: value`` pairs. This keeps every chunk self-describing (column names
travel with the values) which dramatically improves retrieval quality over
dumping a raw grid of numbers.
"""
from __future__ import annotations

from ..models import Element, ElementType, ParsedDocument
from .base import BaseParser, require


def _row_to_text(columns: list[str], values: list) -> str:
    parts = []
    for col, val in zip(columns, values):
        if val is None or str(val).strip() == "" or str(val) == "nan":
            continue
        parts.append(f"{col}: {val}")
    return " | ".join(parts)


class CSVParser(BaseParser):
    name = "csv"

    def parse(self, path: str, source_name: str) -> ParsedDocument:
        pd = require("pandas", "pandas")
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        columns = [str(c) for c in df.columns]
        elements: list[Element] = [
            Element(
                type=ElementType.TITLE,
                text=f"Table '{source_name}' with columns: {', '.join(columns)}",
                metadata={"columns": columns, "n_rows": int(len(df))},
            )
        ]
        for i, (_, row) in enumerate(df.iterrows()):
            text = _row_to_text(columns, list(row.values))
            if text:
                elements.append(
                    Element(type=ElementType.ROW, text=text, metadata={"row": i})
                )
        return ParsedDocument(
            source_name=source_name, parser=self.name, elements=elements,
            metadata={"columns": columns},
        )


class ExcelParser(BaseParser):
    name = "excel"

    def parse(self, path: str, source_name: str) -> ParsedDocument:
        pd = require("pandas", "pandas openpyxl")
        require("openpyxl", "openpyxl")
        sheets = pd.read_excel(path, sheet_name=None, dtype=str, engine="openpyxl")
        elements: list[Element] = []
        for sheet_name, df in sheets.items():
            df = df.fillna("")
            columns = [str(c) for c in df.columns]
            elements.append(
                Element(
                    type=ElementType.TITLE,
                    text=f"Sheet '{sheet_name}' columns: {', '.join(columns)}",
                    metadata={"sheet": sheet_name, "columns": columns},
                )
            )
            for i, (_, row) in enumerate(df.iterrows()):
                text = _row_to_text(columns, list(row.values))
                if text:
                    elements.append(
                        Element(
                            type=ElementType.ROW, text=text,
                            metadata={"sheet": sheet_name, "row": i},
                        )
                    )
        return ParsedDocument(
            source_name=source_name, parser=self.name, elements=elements
        )
