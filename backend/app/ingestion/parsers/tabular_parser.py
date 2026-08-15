"""CSV and Excel parsers.

Tabular data is emitted as one ``ROW`` element per record, each linearized as
``col: value`` pairs. This keeps every chunk self-describing (column names
travel with the values) which dramatically improves retrieval quality over
dumping a raw grid of numbers.
"""
from __future__ import annotations

from ..models import Element, ElementType, ParsedDocument
from .base import BaseParser, ParserError, require


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
        # Read via openpyxl directly (not pandas). pandas loads workbooks in
        # read-only streaming mode, which returns an empty sheet list on files
        # with a malformed workbook spec ("Sheet name is an empty list").
        # The regular loader tolerates those quirks.
        import warnings

        openpyxl = require("openpyxl", "openpyxl")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # ignore benign spec warnings
            workbook = openpyxl.load_workbook(path, data_only=True)

        if not workbook.sheetnames:
            raise ParserError(f"No readable sheets found in '{source_name}'.")

        elements: list[Element] = []
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            header: list[str] | None = None
            row_index = 0
            for raw in sheet.iter_rows(values_only=True):
                if header is None:
                    # First row with any content is the header.
                    if any(c is not None and str(c).strip() for c in raw):
                        header = [
                            str(c).strip() if c is not None else f"col{i}"
                            for i, c in enumerate(raw)
                        ]
                    continue
                values = ["" if c is None else c for c in raw]
                text = _row_to_text(header, values)
                if text:
                    elements.append(
                        Element(type=ElementType.ROW, text=text,
                                metadata={"sheet": sheet_name, "row": row_index})
                    )
                row_index += 1
            if header:
                elements.insert(
                    _sheet_title_position(elements, sheet_name),
                    Element(
                        type=ElementType.TITLE,
                        text=f"Sheet '{sheet_name}' columns: {', '.join(header)}",
                        metadata={"sheet": sheet_name, "columns": header},
                    ),
                )
        return ParsedDocument(
            source_name=source_name, parser=self.name, elements=elements
        )


def _sheet_title_position(elements: list, sheet_name: str) -> int:
    """Index at which this sheet's title element should be inserted (before its
    first row) so titles precede their rows in reading order."""
    for i, el in enumerate(elements):
        if el.metadata.get("sheet") == sheet_name:
            return i
    return len(elements)
