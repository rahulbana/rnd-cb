"""Dispatch an uploaded file to the correct parser based on extension/mime.

The mapping is intentionally explicit so adding a new format is a one-line
change and unsupported types fail fast with a clear message.
"""
from __future__ import annotations

import os

from .models import ParsedDocument
from .parsers.base import BaseParser, ParserError
from .parsers.docx_parser import DocxParser
from .parsers.image_parser import ImageParser
from .parsers.pdf_parser import PDFParser
from .parsers.pptx_parser import PptxParser
from .parsers.tabular_parser import CSVParser, ExcelParser
from .parsers.text_parser import TextParser

# Extension -> parser factory.
_EXTENSION_MAP: dict[str, type[BaseParser] | callable] = {
    ".txt": TextParser,
    ".md": TextParser,
    ".markdown": TextParser,
    ".log": TextParser,
    ".csv": CSVParser,
    ".tsv": CSVParser,
    ".xlsx": ExcelParser,
    ".xls": ExcelParser,
    ".xlsm": ExcelParser,
    ".pdf": PDFParser,
    ".docx": DocxParser,
    ".doc": DocxParser,
    ".pptx": PptxParser,
    ".ppt": PptxParser,
    ".png": ImageParser,
    ".jpg": ImageParser,
    ".jpeg": ImageParser,
    ".webp": ImageParser,
    ".tiff": ImageParser,
    ".bmp": ImageParser,
}

SUPPORTED_EXTENSIONS = sorted(_EXTENSION_MAP.keys())


def get_parser_for(filename: str) -> BaseParser:
    ext = os.path.splitext(filename)[1].lower()
    factory = _EXTENSION_MAP.get(ext)
    if factory is None:
        raise ParserError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    return factory()


def parse_file(path: str, source_name: str) -> ParsedDocument:
    parser = get_parser_for(source_name)
    return parser.parse(path, source_name)


def parse_text(content: str, source_name: str = "pasted-text") -> ParsedDocument:
    """Entry point for raw text pasted directly into the UI."""
    return TextParser().from_string(content, source_name)
