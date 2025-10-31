from pypdf import PdfReader
import uuid
import re


def detect_pdf_type(file_path):
    reader = PdfReader(file_path)
    text_pages = [page.extract_text() for page in reader.pages]
    text_ratio = sum(1 for t in text_pages if t and t.strip()) / len(reader.pages)
    return "text" if text_ratio > 0.5 else "scanned"

def get_uuid4():
    return str(uuid.uuid4())

def clean_text(raw_text: str) -> str:
    """Cleans extracted text by removing excessive whitespace."""
    # Remove multiple spaces, tabs, newlines
    clean_text = re.sub(r'\s+', ' ', raw_text)

    # Remove weird unicode or non-printable chars
    clean_text = re.sub(r'[^\x20-\x7E]+', ' ', clean_text)

    # Strip leading/trailing whitespace
    clean_text = clean_text.strip()

    return clean_text


