import os
from typing import List, Dict, Any
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TesseractCliOcrOptions,
)
from docling.pipeline.simple_pipeline import SimplePipeline
from llama_index.core import Document as LI_Document
from utils import get_uuid4, clean_text

from PIL import Image
import pytesseract


class VisualExtractor:
    """
    VisualExtractor handles scanned PDFs, image-based PDFs, and image files (JPG, PNG, TIFF)
    using Docling for OCR (Tesseract CLI engine) and pytesseract as fallback.
    """

    def __init__(self, ocr_lang: List[str] = ["eng"], force_ocr: bool = True):
        self.ocr_lang = ocr_lang
        self.force_ocr = force_ocr

    def _extract_docling_pdf(self, file_path: str) -> str:
        """Use Docling’s OCR pipeline for PDF (scanned or mixed)."""
        pdf_opts = PdfPipelineOptions()
        pdf_opts.do_ocr = self.force_ocr
        pdf_opts.ocr_options = TesseractCliOcrOptions(
            force_full_page_ocr=True
        )

        self.converter = DocumentConverter(
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.IMAGE,
                InputFormat.DOCX,
                InputFormat.HTML,
                InputFormat.PPTX,
                InputFormat.ASCIIDOC,
                InputFormat.CSV,
                InputFormat.MD,
                InputFormat.XLSX
            ],
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_opts),
                InputFormat.DOCX: WordFormatOption(
                    pipeline_cls = SimplePipeline
                )
            }
        )

        result = self.converter.convert(file_path)
        return result.document.export_to_text()

    def _extract_image(self, file_path: str) -> str:
        """Perform OCR on image files using pytesseract."""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
        except Exception as e:
            text = ''
            print(f"Error during OCR: {e}")
        return text

    def extract(self, file_path: str) -> Dict[str, str]:
        """Automatically detect and extract text from supported formats."""
        ext = os.path.splitext(file_path)[1].lower()
        print(f"Extracting from file: {file_path} with extension: {ext}")
        try:
            if ext in [".pdf", ".docx", ".html", ".pptx", ".ppt", ".md", ".csv", ".xlsx"]:
                print("Using Docling for extraction.")
                text = self._extract_docling_pdf(file_path)
                print("Docling extraction completed.")
            elif ext in [".png", ".jpg", ".jpeg", ".tiff"]:
                print("Using pytesseract for image OCR.")
                text = self._extract_image(file_path)
                print("Image OCR completed.")
            else:
                raise ValueError(f"Unsupported file type: {ext}")
            return {"uuid": get_uuid4(), "text": clean_text(text), "metadata": {"source": os.path.basename(file_path)}}
        except Exception as e:
            return {"error": str(e), "metadata": {"source": os.path.basename(file_path)}}

    def extract_batch(self, file_paths: List[str]) -> List[Dict[str, str]]:
        """Batch process multiple files."""
        return [self.extract(fp) for fp in file_paths]

