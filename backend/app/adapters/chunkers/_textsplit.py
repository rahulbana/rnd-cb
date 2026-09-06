"""Shared text-splitting helpers for chunker adapters."""

from __future__ import annotations

_DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def char_windows(text: str, size: int, overlap: int) -> list[str]:
    """Split ``text`` into fixed-size character windows with overlap."""
    if size <= 0:
        raise ValueError("size must be positive")
    overlap = max(0, min(overlap, size - 1))
    if len(text) <= size:
        return [text] if text else []

    windows: list[str] = []
    start = 0
    step = size - overlap
    while start < len(text):
        window = text[start : start + size]
        if window.strip():
            windows.append(window)
        if start + size >= len(text):
            break
        start += step
    return windows


def recursive_split(
    text: str,
    size: int,
    overlap: int,
    separators: list[str] | None = None,
) -> list[str]:
    """Recursively split on the coarsest separator that keeps pieces <= size.

    Merges small pieces back together greedily so chunks approach ``size``
    without exceeding it, falling back to hard character windows for text with
    no usable separators.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    separators = separators or _DEFAULT_SEPARATORS
    separator = ""
    remaining = separators
    for index, candidate in enumerate(separators):
        if candidate == "":
            separator = ""
            remaining = []
            break
        if candidate in text:
            separator = candidate
            remaining = separators[index + 1 :]
            break

    if separator == "":
        return char_windows(text, size, overlap)

    pieces = [p for p in text.split(separator) if p.strip()]
    chunks: list[str] = []
    buffer = ""
    for piece in pieces:
        if len(piece) > size:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(recursive_split(piece, size, overlap, remaining))
            continue
        candidate = f"{buffer}{separator}{piece}" if buffer else piece
        if len(candidate) <= size:
            buffer = candidate
        else:
            if buffer:
                chunks.append(buffer)
            buffer = piece
    if buffer:
        chunks.append(buffer)
    return chunks
