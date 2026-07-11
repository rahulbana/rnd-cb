"""Citation validation and renumbering.

The Writer asks the LLM to emit inline citations like ``[1]`` / ``[2, 3]``
that map to numbered sources.  Models sometimes cite indices that do not
exist (hallucinated) or leave provided sources uncited.  This module runs a
deterministic post-pass that:

* drops references to non-existent source indices,
* keeps only sources actually referenced in the body,
* renumbers surviving citations sequentially by first appearance, and
* rewrites the inline markers to match the new numbering.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from deep_agent.models.schemas import Citation

# Matches a single citation group: [1], [2, 3], [4,5,6] ...
_CITATION_TOKEN = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


@dataclass
class CitationValidationResult:
    """Outcome of a citation validation pass."""

    body: str
    citations: list[Citation]
    referenced: int = 0          # distinct valid sources actually cited
    dangling_removed: int = 0    # hallucinated numeric references dropped
    unused_dropped: int = 0      # provided sources never cited
    _order: list[int] = field(default_factory=list, repr=False)


def _cleanup_whitespace(text: str) -> str:
    """Tidy spacing left behind after removing citation tokens."""

    # Collapse runs of spaces/tabs created by a removed token.
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Remove a space that now sits before sentence punctuation.
    text = re.sub(r"[ \t]+([.,;:!?)])", r"\1", text)
    # Drop a leftover space right after an opening parenthesis.
    text = re.sub(r"(\()[ \t]+", r"\1", text)
    return text


def validate_citations(
    body: str, citations: list[Citation]
) -> CitationValidationResult:
    """Validate and renumber the inline citations in ``body``.

    Args:
        body: The report body containing ``[n]`` markers.
        citations: The full, source-ordered citation list (indices 1..N).

    Returns:
        A :class:`CitationValidationResult` with the rewritten body and the
        surviving, renumbered citations (ordered by their new index).
    """

    by_index = {c.index: c for c in citations}

    # First pass: establish first-appearance order of *valid* references.
    order: list[int] = []
    seen: set[int] = set()
    for match in _CITATION_TOKEN.finditer(body):
        for part in match.group(1).split(","):
            part = part.strip()
            if not part.isdigit():
                continue
            n = int(part)
            if n in by_index and n not in seen:
                seen.add(n)
                order.append(n)

    remap = {old: new for new, old in enumerate(order, start=1)}
    dangling = 0

    def _replace(match: re.Match) -> str:
        nonlocal dangling
        kept: list[int] = []
        for part in match.group(1).split(","):
            part = part.strip()
            if not part.isdigit():
                continue
            n = int(part)
            if n in remap:
                kept.append(remap[n])
            else:
                dangling += 1
        if not kept:
            return ""  # entire token was hallucinated -> drop it
        ordered = sorted(dict.fromkeys(kept))
        return "[" + ", ".join(str(k) for k in ordered) + "]"

    new_body = _cleanup_whitespace(_CITATION_TOKEN.sub(_replace, body))

    surviving = [
        Citation(index=remap[old], title=by_index[old].title, url=by_index[old].url)
        for old in order
    ]
    surviving.sort(key=lambda c: c.index)

    return CitationValidationResult(
        body=new_body,
        citations=surviving,
        referenced=len(order),
        dangling_removed=dangling,
        unused_dropped=len(by_index) - len(order),
        _order=order,
    )
