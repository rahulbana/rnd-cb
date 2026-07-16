"""Chunking strategies.

Each strategy takes raw text plus a set of parameters and returns a list of
``Chunk`` objects. A ``Chunk`` records the text, its character offsets in the
original document, and (for overlap-aware strategies) how many characters it
shares with the previous chunk. Those offsets let the UI highlight exactly what
each strategy produced and how the chunks relate to one another.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, asdict
from typing import Callable


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Chunk:
    index: int
    text: str
    start: int          # character offset into the source document (inclusive)
    end: int            # character offset (exclusive)
    overlap_prev: int = 0   # chars shared with the previous chunk

    @property
    def char_len(self) -> int:
        return len(self.text)

    @property
    def token_est(self) -> int:
        # Rough, provider-agnostic token estimate. Good enough to reason about
        # sizing without pulling in a heavyweight tokenizer. ~4 chars/token is
        # the widely-cited rule of thumb for English text.
        return max(1, round(len(self.text) / 4))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["char_len"] = self.char_len
        d["token_est"] = self.token_est
        return d


@dataclass
class StrategyParam:
    name: str
    label: str
    type: str                 # "int" | "float" | "bool"
    default: float | int | bool
    min: float | int | None = None
    max: float | int | None = None
    step: float | int | None = None
    help: str = ""


@dataclass
class Strategy:
    key: str
    label: str
    description: str
    params: list[StrategyParam] = field(default_factory=list)
    requires_openai: bool = False


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _find_offsets(text: str, pieces: list[str]) -> list[tuple[int, int]]:
    """Locate each piece sequentially in ``text`` and return (start, end)."""
    offsets = []
    cursor = 0
    for piece in pieces:
        idx = text.find(piece, cursor)
        if idx == -1:  # piece was transformed (e.g. stripped); fall back
            idx = cursor
        start = idx
        end = idx + len(piece)
        offsets.append((start, end))
        cursor = end
    return offsets


# --------------------------------------------------------------------------- #
# Strategy 1 — Fixed-size character chunking (with overlap)
# --------------------------------------------------------------------------- #
def fixed_char(text: str, chunk_size: int = 500, overlap: int = 50, **_) -> list[Chunk]:
    chunk_size = max(1, int(chunk_size))
    overlap = max(0, min(int(overlap), chunk_size - 1))
    step = chunk_size - overlap

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        piece = text[start:end]
        ov = overlap if idx > 0 else 0
        chunks.append(Chunk(index=idx, text=piece, start=start, end=end, overlap_prev=ov))
        idx += 1
        if end == n:
            break
        start += step
    return chunks


# --------------------------------------------------------------------------- #
# Strategy 2 — Recursive character splitting
# --------------------------------------------------------------------------- #
def recursive_char(text: str, chunk_size: int = 500, overlap: int = 50, **_) -> list[Chunk]:
    """Split on a hierarchy of separators, keeping semantically-related text
    together where possible. Mirrors the popular RecursiveCharacterTextSplitter
    idea: try to break on paragraphs, then lines, then sentences, then words,
    then characters — always preferring the largest boundary that fits.
    """
    chunk_size = max(1, int(chunk_size))
    overlap = max(0, min(int(overlap), chunk_size - 1))
    separators = ["\n\n", "\n", ". ", " ", ""]

    def split(txt: str, seps: list[str]) -> list[str]:
        if len(txt) <= chunk_size or not seps:
            return [txt] if txt else []
        sep = seps[0]
        rest = seps[1:]
        parts = txt.split(sep) if sep else list(txt)
        # re-attach the separator so we don't silently lose it
        if sep:
            parts = [p + sep for p in parts[:-1]] + parts[-1:]

        pieces: list[str] = []
        buf = ""
        for part in parts:
            if len(part) > chunk_size:
                if buf:
                    pieces.append(buf)
                    buf = ""
                pieces.extend(split(part, rest))
            elif len(buf) + len(part) <= chunk_size:
                buf += part
            else:
                if buf:
                    pieces.append(buf)
                buf = part
        if buf:
            pieces.append(buf)
        return pieces

    raw_pieces = [p for p in split(text, separators) if p.strip()]

    # Apply character overlap by prepending the tail of the previous piece.
    chunks: list[Chunk] = []
    prev_tail = ""
    cursor = 0
    for i, piece in enumerate(raw_pieces):
        idx = text.find(piece, max(0, cursor - len(prev_tail)))
        if idx == -1:
            idx = cursor
        combined = (prev_tail + piece) if (overlap and i > 0) else piece
        start = idx - len(prev_tail) if (overlap and i > 0) else idx
        start = max(0, start)
        end = idx + len(piece)
        chunks.append(
            Chunk(
                index=i,
                text=combined,
                start=start,
                end=end,
                overlap_prev=len(prev_tail) if i > 0 else 0,
            )
        )
        prev_tail = piece[-overlap:] if overlap else ""
        cursor = end
    return chunks


# --------------------------------------------------------------------------- #
# Strategy 3 — Sentence-based chunking
# --------------------------------------------------------------------------- #
_SENTENCE_RE = re.compile(r"[^.!?]*[.!?]+[\s]*|[^.!?]+$", re.MULTILINE)


def sentence(text: str, sentences_per_chunk: int = 4, overlap_sentences: int = 1, **_) -> list[Chunk]:
    sentences_per_chunk = max(1, int(sentences_per_chunk))
    overlap_sentences = max(0, min(int(overlap_sentences), sentences_per_chunk - 1))
    step = sentences_per_chunk - overlap_sentences

    sents = [s for s in _SENTENCE_RE.findall(text) if s.strip()]
    offsets = _find_offsets(text, sents)

    chunks: list[Chunk] = []
    idx = 0
    i = 0
    while i < len(sents):
        group = sents[i:i + sentences_per_chunk]
        group_offsets = offsets[i:i + sentences_per_chunk]
        piece = "".join(group)
        start = group_offsets[0][0]
        end = group_offsets[-1][1]
        ov = 0
        if idx > 0 and overlap_sentences > 0:
            ov = sum(len(s) for s in sents[i:i + overlap_sentences])
        chunks.append(Chunk(index=idx, text=piece, start=start, end=end, overlap_prev=ov))
        idx += 1
        if i + sentences_per_chunk >= len(sents):
            break
        i += step
    return chunks


# --------------------------------------------------------------------------- #
# Strategy 4 — Paragraph-based chunking
# --------------------------------------------------------------------------- #
def paragraph(text: str, paragraphs_per_chunk: int = 1, **_) -> list[Chunk]:
    paragraphs_per_chunk = max(1, int(paragraphs_per_chunk))
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    offsets = _find_offsets(text, paras)

    chunks: list[Chunk] = []
    idx = 0
    for i in range(0, len(paras), paragraphs_per_chunk):
        group = paras[i:i + paragraphs_per_chunk]
        group_offsets = offsets[i:i + paragraphs_per_chunk]
        piece = "\n\n".join(group)
        start = group_offsets[0][0]
        end = group_offsets[-1][1]
        chunks.append(Chunk(index=idx, text=piece, start=start, end=end, overlap_prev=0))
        idx += 1
    return chunks


# --------------------------------------------------------------------------- #
# Strategy 5 — Token-based (word) chunking
# --------------------------------------------------------------------------- #
def token_word(text: str, tokens_per_chunk: int = 120, overlap: int = 20, **_) -> list[Chunk]:
    """Word-approximate token chunking. Splits on whitespace and groups a fixed
    number of "tokens" (words) per chunk. Language-model tokenizers split more
    finely, but word counts give an intuitive, dependency-free approximation.
    """
    tokens_per_chunk = max(1, int(tokens_per_chunk))
    overlap = max(0, min(int(overlap), tokens_per_chunk - 1))
    step = tokens_per_chunk - overlap

    words = list(re.finditer(r"\S+", text))
    if not words:
        return []

    chunks: list[Chunk] = []
    idx = 0
    i = 0
    while i < len(words):
        group = words[i:i + tokens_per_chunk]
        start = group[0].start()
        end = group[-1].end()
        piece = text[start:end]
        ov = 0
        if idx > 0 and overlap > 0:
            ov_words = words[i:i + overlap]
            if ov_words:
                ov = ov_words[-1].end() - ov_words[0].start()
        chunks.append(Chunk(index=idx, text=piece, start=start, end=end, overlap_prev=ov))
        idx += 1
        if i + tokens_per_chunk >= len(words):
            break
        i += step
    return chunks


# --------------------------------------------------------------------------- #
# Strategy 6 — Semantic chunking (OpenAI embeddings, optional)
# --------------------------------------------------------------------------- #
def semantic(text: str, breakpoint_percentile: int = 90, max_sentences: int = 200, **_) -> list[Chunk]:
    """Group consecutive sentences and start a new chunk wherever the semantic
    similarity between neighbouring sentences drops below a threshold. Uses
    OpenAI embeddings; requires OPENAI_API_KEY. Raises RuntimeError if the key
    or the library is unavailable so the API layer can surface a clear message.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Semantic chunking needs an OpenAI API key. Set OPENAI_API_KEY in "
            "the server environment to enable this strategy."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - env dependent
        raise RuntimeError(
            "The 'openai' package is not installed. Run 'pip install openai' to "
            "enable semantic chunking."
        ) from exc

    sents = [s for s in _SENTENCE_RE.findall(text) if s.strip()]
    if len(sents) <= 1:
        offsets = _find_offsets(text, sents)
        return [
            Chunk(index=0, text="".join(sents), start=offsets[0][0] if offsets else 0,
                  end=offsets[-1][1] if offsets else len(text))
        ]
    sents = sents[: int(max_sentences)]
    offsets = _find_offsets(text, sents)

    client = OpenAI(api_key=api_key)
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=[s.strip() for s in sents],
    )
    vectors = [d.embedding for d in resp.data]

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    # Distance (1 - similarity) between each adjacent sentence pair.
    distances = [1 - cosine(vectors[i], vectors[i + 1]) for i in range(len(vectors) - 1)]
    if distances:
        ordered = sorted(distances)
        k = min(len(ordered) - 1, int(len(ordered) * breakpoint_percentile / 100))
        threshold = ordered[k]
    else:
        threshold = 1.0

    chunks: list[Chunk] = []
    idx = 0
    group_start = 0
    for i, dist in enumerate(distances):
        if dist >= threshold:  # semantic boundary detected between i and i+1
            group = sents[group_start:i + 1]
            start = offsets[group_start][0]
            end = offsets[i][1]
            chunks.append(Chunk(index=idx, text="".join(group), start=start, end=end))
            idx += 1
            group_start = i + 1
    # trailing group
    group = sents[group_start:]
    if group:
        start = offsets[group_start][0]
        end = offsets[-1][1]
        chunks.append(Chunk(index=idx, text="".join(group), start=start, end=end))
    return chunks


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
STRATEGIES: dict[str, Strategy] = {
    "fixed_char": Strategy(
        key="fixed_char",
        label="Fixed-size (characters)",
        description=(
            "Slices the document into fixed-length character windows. Simplest "
            "and fastest, but blind to structure — it will happily cut through "
            "the middle of a word or sentence. Overlap re-includes the tail of "
            "the previous chunk so context isn't lost at the seams."
        ),
        params=[
            StrategyParam("chunk_size", "Chunk size (chars)", "int", 500, 50, 4000, 10,
                          "Number of characters per chunk."),
            StrategyParam("overlap", "Overlap (chars)", "int", 50, 0, 1000, 10,
                          "Characters repeated from the end of the previous chunk."),
        ],
    ),
    "recursive_char": Strategy(
        key="recursive_char",
        label="Recursive character",
        description=(
            "Tries to break on the largest natural boundary that fits — "
            "paragraph, then line, then sentence, then word, then character. "
            "Keeps related text together far better than the fixed slicer while "
            "still respecting a maximum size. This is the common default in RAG "
            "pipelines."
        ),
        params=[
            StrategyParam("chunk_size", "Max chunk size (chars)", "int", 500, 50, 4000, 10,
                          "Upper bound on chunk length."),
            StrategyParam("overlap", "Overlap (chars)", "int", 50, 0, 1000, 10,
                          "Characters carried over from the previous chunk."),
        ],
    ),
    "sentence": Strategy(
        key="sentence",
        label="Sentence-based",
        description=(
            "Groups a fixed number of whole sentences per chunk. Guarantees no "
            "sentence is ever split, so each chunk reads as complete thoughts. "
            "Chunk sizes vary with sentence length."
        ),
        params=[
            StrategyParam("sentences_per_chunk", "Sentences per chunk", "int", 4, 1, 50, 1,
                          "How many sentences go into each chunk."),
            StrategyParam("overlap_sentences", "Overlap (sentences)", "int", 1, 0, 10, 1,
                          "Sentences repeated from the previous chunk."),
        ],
    ),
    "paragraph": Strategy(
        key="paragraph",
        label="Paragraph-based",
        description=(
            "Splits on blank lines, treating each paragraph (or group of "
            "paragraphs) as a chunk. Preserves the author's structure exactly, "
            "but produces very uneven chunk sizes depending on the document."
        ),
        params=[
            StrategyParam("paragraphs_per_chunk", "Paragraphs per chunk", "int", 1, 1, 20, 1,
                          "How many paragraphs go into each chunk."),
        ],
    ),
    "token_word": Strategy(
        key="token_word",
        label="Token-based (word approx.)",
        description=(
            "Groups a fixed number of whitespace tokens (words) per chunk — an "
            "intuitive stand-in for model-token budgeting without a tokenizer. "
            "Useful when you want to keep chunks under a rough token limit."
        ),
        params=[
            StrategyParam("tokens_per_chunk", "Tokens per chunk", "int", 120, 10, 2000, 10,
                          "Number of words per chunk."),
            StrategyParam("overlap", "Overlap (tokens)", "int", 20, 0, 500, 5,
                          "Words repeated from the previous chunk."),
        ],
    ),
    "semantic": Strategy(
        key="semantic",
        label="Semantic (OpenAI embeddings)",
        description=(
            "Embeds every sentence with OpenAI and starts a new chunk wherever "
            "the meaning shifts (similarity between neighbouring sentences "
            "drops). Produces topically-coherent chunks. Requires OPENAI_API_KEY."
        ),
        requires_openai=True,
        params=[
            StrategyParam("breakpoint_percentile", "Breakpoint percentile", "int", 90, 50, 99, 1,
                          "Higher = fewer, larger chunks. Boundaries are placed at "
                          "similarity drops above this percentile."),
            StrategyParam("max_sentences", "Max sentences (cost cap)", "int", 200, 10, 1000, 10,
                          "Caps how many sentences are embedded to bound API cost."),
        ],
    ),
}

DISPATCH: dict[str, Callable[..., list[Chunk]]] = {
    "fixed_char": fixed_char,
    "recursive_char": recursive_char,
    "sentence": sentence,
    "paragraph": paragraph,
    "token_word": token_word,
    "semantic": semantic,
}


def run_strategy(key: str, text: str, params: dict) -> list[Chunk]:
    if key not in DISPATCH:
        raise ValueError(f"Unknown chunking strategy: {key!r}")
    return DISPATCH[key](text, **params)
