"""Query understanding: light rewriting + metadata-filter extraction.

Rule-based and deterministic (no LLM) so retrieval quality can be measured on
its own. An LLM-backed rewriter can replace ``QueryProcessor`` behind the same
shape later. Extracts a year and a document-type hint the retrieval service
resolves into a document-id scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_WS_RE = re.compile(r"\s+")

# Document-type keyword -> MIME prefixes it should match.
_DOC_TYPE_MIME: dict[str, tuple[str, ...]] = {
    "pdf": ("application/pdf",),
    "word": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
    "image": ("image/",),
    "scan": ("image/",),
    "markdown": ("text/markdown",),
    "text": ("text/plain",),
}


@dataclass
class QueryFilters:
    year: int | None = None
    doc_type: str | None = None
    mime_prefixes: tuple[str, ...] = ()

    def is_empty(self) -> bool:
        return self.year is None and self.doc_type is None


@dataclass
class QueryPlan:
    original: str
    text: str  # rewritten/normalized query used for retrieval
    filters: QueryFilters = field(default_factory=QueryFilters)


class QueryProcessor:
    """Normalizes a query and extracts metadata filters from it."""

    def process(self, query: str) -> QueryPlan:
        original = query
        filters = QueryFilters()

        year_match = _YEAR_RE.search(query)
        if year_match:
            filters.year = int(year_match.group(0))

        lowered = query.lower()
        for keyword, prefixes in _DOC_TYPE_MIME.items():
            if re.search(rf"\b{re.escape(keyword)}s?\b", lowered):
                filters.doc_type = keyword
                filters.mime_prefixes = prefixes
                break

        text = _WS_RE.sub(" ", query).strip()
        return QueryPlan(original=original, text=text, filters=filters)
