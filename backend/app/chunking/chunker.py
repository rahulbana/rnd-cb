"""Chunking strategies.

The default (``recursive``) is a structure-aware, token-budgeted packer: it
walks the document's elements in order and greedily packs them into chunks up
to ``chunk_size_tokens``, with ``chunk_overlap_tokens`` of trailing context
carried into the next chunk. Element boundaries are respected, and atomic
elements (tables, rows) are never split mid-record. Oversized prose elements
are recursively split on paragraph/sentence/word boundaries.

Alternative strategies:
  * ``by_element``  - one chunk per source element (good for dense tabular data).
  * ``semantic``    - split where adjacent sentence embeddings diverge, so
                      chunks track topic shifts rather than a fixed size.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from pydantic import BaseModel, Field

from ..config import get_settings
from ..ingestion.models import Element, ElementType, ParsedDocument

# --- token counting ---------------------------------------------------------
try:
    import tiktoken

    _enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))

    def _split_by_tokens(text: str, limit: int) -> list[str]:
        ids = _enc.encode(text)
        return [_enc.decode(ids[i:i + limit]) for i in range(0, len(ids), limit)]
except Exception:  # pragma: no cover - tiktoken optional
    def count_tokens(text: str) -> int:
        # ~4 chars/token heuristic fallback.
        return max(1, len(text) // 4)

    def _split_by_tokens(text: str, limit: int) -> list[str]:
        approx = limit * 4
        return [text[i:i + approx] for i in range(0, len(text), approx)]


class Chunk(BaseModel):
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    n_tokens: int = 0


_ATOMIC = {ElementType.TABLE, ElementType.ROW}
_SPLIT_PATTERNS = ["\n\n", "\n", r"(?<=[.!?])\s+", " "]


def _recursive_split(text: str, limit: int) -> list[str]:
    """Split an oversized text down to <= limit tokens, preferring natural
    boundaries (paragraphs -> lines -> sentences -> words -> hard tokens)."""
    if count_tokens(text) <= limit:
        return [text]
    for pattern in _SPLIT_PATTERNS:
        parts = re.split(pattern, text)
        if len(parts) < 2:
            continue
        out: list[str] = []
        for part in parts:
            if not part.strip():
                continue
            if count_tokens(part) <= limit:
                out.append(part)
            else:
                out.extend(_recursive_split(part, limit))
        if out:
            return out
    # Nothing to split on: hard cut by tokens.
    return _split_by_tokens(text, limit)


def _overlap_tail(text: str, overlap_tokens: int) -> str:
    if overlap_tokens <= 0:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    tail: list[str] = []
    total = 0
    for sent in reversed(sentences):
        total += count_tokens(sent)
        tail.insert(0, sent)
        if total >= overlap_tokens:
            break
    return " ".join(tail)


class Chunker:
    def __init__(self, strategy: str | None = None, size: int | None = None,
                 overlap: int | None = None) -> None:
        s = get_settings()
        self.strategy = strategy or s.chunk_strategy
        self.size = size or s.chunk_size_tokens
        self.overlap = overlap if overlap is not None else s.chunk_overlap_tokens

    def chunk(self, doc: ParsedDocument) -> list[Chunk]:
        strategies: dict[str, Callable[[ParsedDocument], list[Chunk]]] = {
            "recursive": self._recursive,
            "by_element": self._by_element,
            "semantic": self._semantic,
        }
        fn = strategies.get(self.strategy, self._recursive)
        chunks = fn(doc)
        for i, ch in enumerate(chunks):
            ch.metadata.setdefault("source", doc.source_name)
            ch.metadata["chunk_index"] = i
            ch.n_tokens = count_tokens(ch.text)
        return chunks

    # --- recursive structure-aware packing (default) ------------------------
    def _recursive(self, doc: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        buffer: list[str] = []
        buffer_meta: list[dict] = []
        buf_tokens = 0

        def flush() -> None:
            nonlocal buffer, buffer_meta, buf_tokens
            if not buffer:
                return
            text = "\n".join(buffer).strip()
            if text:
                chunks.append(Chunk(text=text, metadata=_merge_meta(buffer_meta)))
            carry = _overlap_tail(text, self.overlap)
            buffer = [carry] if carry else []
            buffer_meta = []
            buf_tokens = count_tokens(carry) if carry else 0

        for el in doc.elements:
            pieces = [el.text] if el.type in _ATOMIC else _recursive_split(el.text, self.size)
            for piece in pieces:
                ptoks = count_tokens(piece)
                if buf_tokens + ptoks > self.size and buffer:
                    flush()
                buffer.append(piece)
                buffer_meta.append(el.metadata)
                buf_tokens += ptoks
        flush()
        # Drop a trailing chunk that is only carried-over overlap.
        return [c for c in chunks if c.text.strip()]

    # --- one chunk per element ----------------------------------------------
    def _by_element(self, doc: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        for el in doc.elements:
            for piece in _recursive_split(el.text, self.size):
                if piece.strip():
                    chunks.append(Chunk(text=piece, metadata=dict(el.metadata)))
        return chunks

    # --- semantic (embedding-drift boundaries) ------------------------------
    def _semantic(self, doc: ParsedDocument) -> list[Chunk]:
        try:
            from ..embeddings import get_embedder
            import numpy as np
        except Exception:
            return self._recursive(doc)

        sentences: list[tuple[str, dict]] = []
        for el in doc.elements:
            for sent in re.split(r"(?<=[.!?])\s+", el.text):
                if sent.strip():
                    sentences.append((sent.strip(), el.metadata))
        if len(sentences) < 3:
            return self._recursive(doc)

        embedder = get_embedder()
        vectors = np.array(embedder.embed([s for s, _ in sentences]))
        vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9)
        sims = [float(vectors[i] @ vectors[i + 1]) for i in range(len(vectors) - 1)]
        threshold = float(np.percentile(sims, 25)) if sims else 0.0

        chunks: list[Chunk] = []
        cur: list[str] = []
        cur_meta: list[dict] = []
        cur_tokens = 0
        for i, (sent, meta) in enumerate(sentences):
            cur.append(sent)
            cur_meta.append(meta)
            cur_tokens += count_tokens(sent)
            boundary = i < len(sims) and sims[i] < threshold
            if cur and (cur_tokens >= self.size or boundary):
                chunks.append(Chunk(text=" ".join(cur), metadata=_merge_meta(cur_meta)))
                cur, cur_meta, cur_tokens = [], [], 0
        if cur:
            chunks.append(Chunk(text=" ".join(cur), metadata=_merge_meta(cur_meta)))
        return chunks


def _merge_meta(metas: list[dict]) -> dict:
    """Collapse per-element metadata into a chunk-level summary (e.g. page span)."""
    merged: dict[str, Any] = {}
    pages = sorted({m["page"] for m in metas if "page" in m})
    if pages:
        merged["pages"] = pages
        merged["page"] = pages[0]
    for key in ("sheet", "slide", "table"):
        vals = sorted({m[key] for m in metas if key in m})
        if vals:
            merged[key] = vals[0] if len(vals) == 1 else vals
    return merged
