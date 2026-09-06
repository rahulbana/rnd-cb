"""Parser adapters."""

from app.adapters.parsers.docling_parser import DoclingParser
from app.adapters.parsers.docx_parser import DocxParser
from app.adapters.parsers.fake_parser import FakeParser
from app.adapters.parsers.image_parser import TesseractImageParser
from app.adapters.parsers.plain_parser import PlainTextParser
from app.adapters.parsers.pymupdf_parser import PyMuPDFParser
from app.adapters.parsers.router import ParserError, ParserRouter
from app.adapters.parsers.unstructured_parser import UnstructuredParser

__all__ = [
    "DoclingParser",
    "DocxParser",
    "FakeParser",
    "ParserError",
    "ParserRouter",
    "PlainTextParser",
    "PyMuPDFParser",
    "TesseractImageParser",
    "UnstructuredParser",
]
