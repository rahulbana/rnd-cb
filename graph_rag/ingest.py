"""Load .txt documents and split them into overlapping chunks.

Chunking keeps each LLM extraction call small and focused. Overlap avoids
losing relationships that straddle a chunk boundary.
"""

from dataclasses import dataclass
from pathlib import Path

from . import config


@dataclass
class Chunk:
    """One slice of a source document."""

    source: str  # file name the chunk came from
    index: int  # position of the chunk within that file
    text: str


def load_documents(data_dir: str) -> list[tuple[str, str]]:
    """Return (filename, text) for every .txt file in data_dir."""
    directory = Path(data_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    docs: list[tuple[str, str]] = []
    for path in sorted(directory.glob("*.txt")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            docs.append((path.name, text))

    if not docs:
        raise ValueError(f"No non-empty .txt files found in {data_dir}")
    return docs


def chunk_text(
    text: str,
    size: int = config.CHUNK_SIZE,
    overlap: int = config.CHUNK_OVERLAP,
) -> list[str]:
    """Split text into character windows of `size` that overlap by `overlap`."""
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap >= size:
        raise ValueError("overlap must be smaller than chunk size")

    chunks: list[str] = []
    start = 0
    step = size - overlap
    while start < len(text):
        chunk = text[start : start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def build_chunks(data_dir: str) -> list[Chunk]:
    """Load every document and flatten it into a list of Chunk objects."""
    chunks: list[Chunk] = []
    for filename, text in load_documents(data_dir):
        for i, piece in enumerate(chunk_text(text)):
            chunks.append(Chunk(source=filename, index=i, text=piece))
    return chunks
