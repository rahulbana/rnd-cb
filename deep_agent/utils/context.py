"""Input-context budgeting.

Builds a numbered ``[i] title (url)\\ncontent`` block from scraped documents
while capping both per-source length and total size, so the prompts sent to
the Reflection / Fact-Checker / Writer agents stay within a token budget.
This reduces input-token cost/latency and prevents context overflow.
"""
from __future__ import annotations

from deep_agent.models.schemas import ScrapedDocument


def build_sources_block(
    docs: list[ScrapedDocument],
    total_chars: int,
    per_source_chars: int,
    start_index: int = 1,
) -> tuple[str, list[ScrapedDocument]]:
    """Return ``(block, included_docs)`` within the given char budgets.

    Documents are added in order until ``total_chars`` is exhausted; the
    returned ``included_docs`` are exactly those represented in the block
    (so callers can keep citations aligned with what the model actually saw).
    """

    parts: list[str] = []
    included: list[ScrapedDocument] = []
    used = 0

    for offset, doc in enumerate(docs):
        index = start_index + offset
        header = f"[{index}] {doc.title or doc.url} ({doc.url})"
        snippet = doc.content[:per_source_chars]
        block = f"{header}\n{snippet}"

        if used + len(block) > total_chars:
            remaining = total_chars - used
            # Only include a truncated tail if there's room for the header
            # plus a little content; otherwise stop.
            if remaining < len(header) + 200:
                break
            block = block[:remaining]

        parts.append(block)
        included.append(doc)
        used += len(block)
        if used >= total_chars:
            break

    return ("\n\n".join(parts) or "(no sources available)", included)
