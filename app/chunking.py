"""Text-processing helpers for context-window management.

When a document is too large to summarize in a single request, we split it into
chunks on natural boundaries (paragraphs, then sentences, then a hard character
cut as a last resort), summarize each, and combine the results.
"""

from __future__ import annotations

import re

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"[^.!?]+[.!?]+[\])'\"`]*\s*|[^.!?]+$")


def approx_tokens(text: str) -> int:
    """Rough token estimate for English text (~4 chars/token)."""
    return -(-len(text) // 4)  # ceil division


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks no larger than ``max_chars``, preferring paragraph
    breaks, then sentence breaks, and only hard-splitting a run with neither."""
    trimmed = text.strip()
    if len(trimmed) <= max_chars:
        return [trimmed]

    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for para in _PARAGRAPH_SPLIT.split(trimmed):
        if len(para) > max_chars:
            # A single oversized paragraph: flush what we have, then break it down.
            flush()
            chunks.extend(_split_large_block(para, max_chars))
            continue
        if len(current) + len(para) + 2 > max_chars:
            flush()
        current += ("\n\n" if current else "") + para
    flush()

    return chunks


def _split_large_block(block: str, max_chars: int) -> list[str]:
    """Break an oversized block on sentence boundaries, falling back to a hard cut."""
    sentences = _SENTENCE_SPLIT.findall(block) or [block]
    out: list[str] = []
    current = ""

    for sentence in sentences:
        if len(sentence) > max_chars:
            if current.strip():
                out.append(current.strip())
            current = ""
            for i in range(0, len(sentence), max_chars):
                out.append(sentence[i : i + max_chars])
            continue
        if len(current) + len(sentence) > max_chars:
            out.append(current.strip())
            current = ""
        current += sentence

    if current.strip():
        out.append(current.strip())
    return out
