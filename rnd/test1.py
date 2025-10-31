#from docling import DocumentConverter
from docling.document_converter import DocumentConverter


converter = DocumentConverter()
result = converter.convert("./Unit_Statement_28-04-2025-28-10-2025.pdf")

# Extract text (docling handles text + OCR)
text = result.document.export_to_text()
print(text[:500])
