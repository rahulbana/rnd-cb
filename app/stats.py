"""Impact analysis for a set of chunks.

The point of the tool is not just to show chunks, but to make the *consequences*
of a chunking strategy legible: how big the chunks are, how uniform, how much
redundancy overlap introduces, and how often the strategy severs a sentence or
a word. These metrics are what actually differ between strategies for the same
document.
"""

from __future__ import annotations

import statistics
from typing import Iterable

from .chunkers import Chunk


def _pct(part: float, whole: float) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def analyze(chunks: list[Chunk], source_text: str) -> dict:
    if not chunks:
        return {"chunk_count": 0, "empty": True}

    char_lens = [c.char_len for c in chunks]
    token_ests = [c.token_est for c in chunks]
    overlaps = [c.overlap_prev for c in chunks]

    total_chunk_chars = sum(char_lens)
    source_len = len(source_text)
    overlap_chars = sum(overlaps)

    # How often does a chunk boundary fall in the middle of a word or sentence?
    mid_word = 0
    mid_sentence = 0
    for c in chunks:
        # boundary at the END of the chunk within the source
        if 0 < c.end < source_len:
            before = source_text[c.end - 1]
            after = source_text[c.end]
            if before.isalnum() and after.isalnum():
                mid_word += 1
            # sentence considered "cut" if the char before the boundary is not
            # sentence-terminating punctuation / whitespace
            if before not in ".!?\n" and not before.isspace() and after not in " \n":
                mid_sentence += 1

    stdev = statistics.pstdev(char_lens) if len(char_lens) > 1 else 0.0
    mean = statistics.mean(char_lens)
    # Coefficient of variation: uniformity of chunk sizes (lower = more uniform)
    cv = round(stdev / mean, 3) if mean else 0.0

    return {
        "empty": False,
        "chunk_count": len(chunks),
        "source_chars": source_len,
        "source_tokens_est": max(1, round(source_len / 4)),
        "char_len": {
            "min": min(char_lens),
            "max": max(char_lens),
            "mean": round(mean, 1),
            "median": round(statistics.median(char_lens), 1),
            "stdev": round(stdev, 1),
            "cv": cv,
        },
        "token_est": {
            "min": min(token_ests),
            "max": max(token_ests),
            "mean": round(statistics.mean(token_ests), 1),
            "total": sum(token_ests),
        },
        "overlap": {
            "total_chars": overlap_chars,
            "chunks_with_overlap": sum(1 for o in overlaps if o > 0),
            # Redundancy = extra characters stored because of overlap, relative
            # to the original document. A direct measure of storage/embedding
            # cost the strategy adds.
            "redundancy_pct": _pct(overlap_chars, source_len),
        },
        "boundaries": {
            "mid_word_cuts": mid_word,
            "mid_word_pct": _pct(mid_word, len(chunks)),
            "mid_sentence_cuts": mid_sentence,
            "mid_sentence_pct": _pct(mid_sentence, len(chunks)),
        },
        "coverage_pct": _pct(min(total_chunk_chars, source_len), source_len),
        # Data for the histogram in the UI.
        "histogram": _histogram(char_lens),
    }


def _histogram(values: Iterable[int], bins: int = 12) -> dict:
    values = list(values)
    lo, hi = min(values), max(values)
    if lo == hi:
        return {"edges": [lo, hi], "counts": [len(values)], "labels": [str(lo)]}
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        i = min(bins - 1, int((v - lo) / width))
        counts[i] += 1
    edges = [round(lo + i * width) for i in range(bins + 1)]
    labels = [f"{edges[i]}–{edges[i+1]}" for i in range(bins)]
    return {"edges": edges, "counts": counts, "labels": labels}
