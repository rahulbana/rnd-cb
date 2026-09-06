# ADR 0004 — Chunking, embedding & vector storage

- Status: Accepted
- Date: 2026-09-06
- Phase: 3

## Context

Parsed documents must become a searchable vector index, with the chunker,
embedder, and vector store each independently swappable, and org isolation
built in from the start.

## Decision

Three new ports gain real adapters behind the existing interfaces:

- **Chunker** — `structure_aware` (default; groups by heading, packs to size,
  keeps tables and page/heading provenance), `fixed_size`, `recursive`. All
  pure-Python and fully tested.
- **Embedder** — `sentence_transformers` (local, free, default) and `openai`.
  Both lazy-load their heavy client on first use; `EmbeddingVector.dim` is
  declared from config so drift is detectable.
- **VectorStore** — `chroma` (default; HTTP for compose/prod, ephemeral/
  persistent for dev/tests) and `pgvector` (vectors alongside relational
  metadata). Both use cosine similarity so a swap is behaviourally consistent.

`IngestionService` orchestrates chunk → embed → upsert within an org
**namespace** (Chroma collection / pgvector `namespace` column) — the
multi-tenancy hook. `DocumentService` runs the full pipeline on upload and
persists `chunks_meta` rows (page, heading, `vector_id`) while the vectors live
in the store. `POST /api/v1/documents/search` exposes raw dense similarity
search (hybrid retrieval + reranking arrive in Phases 5-6).

Heavy dependencies (sentence-transformers, chromadb, pgvector) are an `ml`
extra installed in the container image; the base/dev install stays light.
Adapter construction never imports them, so the registry resolves defaults and
CI runs without the ML stack. Tests use the deterministic fakes for the
end-to-end path and exercise the real Chroma adapter via an embedded client;
pgvector's live test is gated on a real Postgres.

## Consequences

- Switching `VECTOR_STORE_PROVIDER` (chroma ↔ pgvector ↔ fake) or
  `EMBEDDER_PROVIDER` is one env value; the call site is unchanged, proven by
  `tests/test_vector_store_swap.py`.
- A document ingests end-to-end and is retrievable by raw similarity
  (`tests/test_ingestion.py`, `tests/test_upload.py::test_upload_then_search_end_to_end`).
- Embedding-dimension drift on an embedder swap is a documented reindex (ADR
  runbook), aided by the explicit `dim` on every vector.
