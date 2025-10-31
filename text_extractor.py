import os
from typing import List, Dict, Any
from utils import get_uuid4, clean_text

class TextExtractor:
    """Extracts text content from text-based documents for LlamaIndex ingestion."""

    def __init__(self):
        pass

    def extract(self, file_path: str) -> List[Dict[str, Any]]:
        """Auto-detect document type and extract text.

        Returns:
            List of dicts: [{"text": str, "metadata": {"source": str, ...}}]
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".txt":
            return self._from_text(file_path)
        else:
            raise ValueError(f"Unsupported or missing dependency for file type: {ext}")

    def _from_text(self, path: str) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return [{"uuid": get_uuid4(), "text": clean_text(text), "metadata": {"source": os.path.basename(path)}}]
