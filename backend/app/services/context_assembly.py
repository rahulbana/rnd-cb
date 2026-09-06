"""Context assembly: turn reranked chunks into a token-budgeted, cited context.

Steps, in order:
  1. dedup near-identical chunks (token-Jaccard threshold)
  2. MMR pass -- trade relevance against diversity so the context isn't three
     paraphrases of the same passage
  3. optional contextual compression -- drop sentences with no query-term overlap
  4. pack to a token budget using a provider-specific token counter
  5. tag citations -- each kept chunk -> source document + page

The token counter is injected (default: whitespace words); Phase 7 passes the
active LLM provider's ``count_tokens`` so budgeting matches the real tokenizer.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from app.domain.models import Citation, RetrievedChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _word_count(text: str) -> int:
    return len(text.split())


@dataclass
class AssembledContext:
    text: str
    citations: list[Citation] = field(default_factory=list)
    chunks: list[RetrievedChunk] = field(default_factory=list)


class ContextAssembler:
    """Dedups, diversifies, budgets, and cites reranked chunks."""

    def __init__(
        self,
        *,
        token_budget: int = 2000,
        mmr_lambda: float = 0.7,
        dedup_threshold: float = 0.9,
        count_tokens: Callable[[str], int] = _word_count,
        compress: bool = False,
    ) -> None:
        self._budget = token_budget
        self._lambda = mmr_lambda
        self._dedup = dedup_threshold
        self._count = count_tokens
        self._compress = compress

    def assemble(
        self, query: str, candidates: Sequence[RetrievedChunk]
    ) -> AssembledContext:
        deduped = self._dedup_chunks(candidates)
        ordered = self._mmr(deduped)

        query_tokens = _tokens(query)
        selected: list[RetrievedChunk] = []
        used = 0
        for item in ordered:
            text = item.chunk.text
            if self._compress:
                text = self._compress_text(text, query_tokens)
            cost = self._count(text)
            if selected and used + cost > self._budget:
                break
            selected.append(
                RetrievedChunk(
                    chunk=item.chunk.model_copy(update={"text": text}),
                    score=item.score,
                    source=item.source,
                )
            )
            used += cost

        return AssembledContext(
            text=self._render(selected),
            citations=[self._cite(i, c) for i, c in enumerate(selected, start=1)],
            chunks=selected,
        )

    # --- steps ---------------------------------------------------------------

    def _dedup_chunks(self, candidates: Sequence[RetrievedChunk]) -> list[RetrievedChunk]:
        kept: list[RetrievedChunk] = []
        kept_tokens: list[set[str]] = []
        for item in candidates:
            toks = _tokens(item.chunk.text)
            if any(_jaccard(toks, prev) >= self._dedup for prev in kept_tokens):
                continue
            kept.append(item)
            kept_tokens.append(toks)
        return kept

    def _mmr(self, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if len(candidates) <= 1:
            return list(candidates)
        # Normalize relevance to [0, 1] so it is comparable to the Jaccard sim.
        scores = [c.score for c in candidates]
        lo, hi = min(scores), max(scores)
        span = (hi - lo) or 1.0
        rel = {id(c): (c.score - lo) / span for c in candidates}
        toks = {id(c): _tokens(c.chunk.text) for c in candidates}

        remaining = list(candidates)
        selected: list[RetrievedChunk] = []
        while remaining:
            best = None
            best_val = float("-inf")
            for cand in remaining:
                if not selected:
                    val = rel[id(cand)]
                else:
                    max_sim = max(_jaccard(toks[id(cand)], toks[id(s)]) for s in selected)
                    val = self._lambda * rel[id(cand)] - (1 - self._lambda) * max_sim
                if val > best_val:
                    best_val, best = val, cand
            assert best is not None
            selected.append(best)
            remaining.remove(best)
        return selected

    def _compress_text(self, text: str, query_tokens: set[str]) -> str:
        sentences = _SENTENCE_RE.split(text)
        if len(sentences) <= 1:
            return text
        kept = [s for s in sentences if _tokens(s) & query_tokens]
        return " ".join(kept) if kept else text

    def _render(self, selected: Sequence[RetrievedChunk]) -> str:
        return "\n\n".join(
            f"[{i}] {c.chunk.text}" for i, c in enumerate(selected, start=1)
        )

    def _cite(self, index: int, item: RetrievedChunk) -> Citation:
        return Citation(
            chunk_id=item.chunk.id,
            document_id=item.chunk.metadata.document_id,
            page=item.chunk.metadata.page,
            heading_path=item.chunk.metadata.heading_path,
            score=item.score,
        )
