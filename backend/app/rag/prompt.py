"""Prompt construction for grounded, cite-able answers."""
from __future__ import annotations

from ..retrieval.base import RetrievedChunk

SYSTEM_PROMPT = (
    "You are an enterprise knowledge assistant. Answer the user's question "
    "using ONLY the numbered context passages provided. Cite the passages you "
    "use inline with bracketed numbers like [1], [2]. If the answer is not "
    "contained in the context, say you don't have that information rather than "
    "guessing. Be concise and accurate."
)


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        src = chunk.metadata.get("source", "unknown")
        loc = ""
        if "page" in chunk.metadata:
            loc = f", p.{chunk.metadata['page']}"
        elif "slide" in chunk.metadata:
            loc = f", slide {chunk.metadata['slide']}"
        lines.append(f"[{i}] (source: {src}{loc})\n{chunk.text}")
    return "\n\n".join(lines)


def build_messages(query: str, chunks: list[RetrievedChunk]) -> list[dict]:
    context = build_context_block(chunks) if chunks else "(no relevant context found)"
    user = (
        f"Context passages:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer using the context above and cite sources with [n]."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def sources_payload(chunks: list[RetrievedChunk]) -> list[dict]:
    """Compact, UI-friendly view of the passages used as context."""
    out = []
    for i, c in enumerate(chunks, start=1):
        out.append({
            "n": i,
            "source": c.metadata.get("source", "unknown"),
            "page": c.metadata.get("page"),
            "slide": c.metadata.get("slide"),
            "score": round(c.score, 4),
            "scores": {k: round(v, 4) for k, v in c.scores.items()},
            "preview": c.text[:280] + ("…" if len(c.text) > 280 else ""),
        })
    return out
