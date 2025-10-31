from pypdf import PdfReader


def detect_pdf_type(file_path):
    reader = PdfReader(file_path)
    text_pages = [page.extract_text() for page in reader.pages]
    text_ratio = sum(1 for t in text_pages if t and t.strip()) / len(reader.pages)
    return "text" if text_ratio > 0.5 else "scanned"


if __name__ == "__main__":
    # file_path = "./Unit_Statement_28-04-2025-28-10-2025.pdf"
    file_path = "./scansmpl.pdf"
    # file_path = "./Unit_Statement_28-04-2025-28-10-2025.pdf"
    pdf_type = detect_pdf_type(file_path)
    print(f"The PDF is detected as: {pdf_type}")
