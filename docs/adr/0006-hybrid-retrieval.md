# ADR 0006 — Hybrid retrieval & query understanding

- Status: Accepted
- Date: 2026-09-06
- Phase: 5

## Context

Dense (semantic) retrieval misses exact terms, rare tokens, names, and codes;
lexical retrieval misses paraphrases. Retrieval quality must be measurable on
its own, independent of generation, and scopable per document/collection.

## Decision

Three retriever adapters behind the `Retriever` port:

- **dense** — embeds the query and searches the vector store.
- **sparse** — BM25 over `chunks_meta.text` (chunk text is now kept in Postgres
  as well as the vector store), scoped by org namespace and optional document
  ids. A Postgres full-text variant can replace it behind the same port.
- **hybrid** (default) — fuses dense + sparse with **Reciprocal Rank Fusion**
  (`score = Σ 1/(RRF_K + rank)`), which needs no score calibration between the
  two arms.

**Query understanding** (`QueryProcessor`) is rule-based and deterministic: it
normalizes the query and extracts a year and a document-type hint. The
`RetrievalService` resolves those filters into a document-id scope (via the
`documents` table) before the retriever runs — so "the pdf about revenue from
2023" retrieves only within 2023 PDFs. An LLM-backed rewriter can replace the
processor behind the same shape later.

A standalone `POST /api/v1/retrieve` exposes retrieval without generation, with
a per-request `strategy` override (dense/sparse/hybrid) and `document_ids`
scoping — so strategies can be compared directly.

`app/evaluation/retrieval_eval.py` scores a retriever against a labeled query
set (recall@k, MRR) and logs the numbers.

## Consequences

- The `Retriever.retrieve` signature gains an optional `document_ids` scope.
- Chunk text is stored in Postgres (migration `0002`) to give lexical search a
  corpus; the sparse retriever gates on lexical overlap so BM25's negative-IDF
  behavior on tiny/uniform corpora can't drop valid matches.
- Exit (measured, logged, not asserted): on a 12-doc corpus with a 5-query
  labeled set, hybrid recall@3 = 1.0 vs dense-only 0.2 —
  `tests/test_retrieval_eval.py`.
