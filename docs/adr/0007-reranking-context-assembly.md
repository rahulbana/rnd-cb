# ADR 0007 — Reranking & context assembly

- Status: Accepted
- Date: 2026-09-06
- Phase: 6

## Context

First-stage retrieval (bi-encoder + BM25) favors recall; the truly relevant
chunks still need to be pushed to the top and packed into a token-budgeted,
citation-tagged context before generation.

## Decision

**Rerankers** behind the `Reranker` port re-score an over-fetched candidate set
(`RERANK_FETCH_K`) down to `top_k`:

- **cross_encoder** (default) — a sentence-transformers CrossEncoder scores
  (query, passage) pairs jointly; far more precise than retrieval similarity,
  run only over candidates. Torch loads lazily.
- **cohere** — hosted Cohere Rerank (opt-in extra).
- **llm** — prompts the configured LLM (via the LLMProvider port) to rate each
  candidate 0-10; scores parsed defensively.

**ContextAssembler** turns reranked chunks into the final context, in order:
dedup near-identical chunks (token-Jaccard), an **MMR** pass trading relevance
against diversity, optional contextual compression (drop sentences with no
query-term overlap), packing to a **token budget** with an injected token
counter (Phase 7 passes the active LLM's `count_tokens`), and **citation
tagging** (each kept chunk → source document + page). Output is the rendered
`[n]`-marked context plus a parallel list of `Citation`s.

A `rerank=true` flag on `POST /api/v1/retrieve` exposes the retrieve→rerank
pipeline for comparison; the eval harness now also reports precision@k and can
score a reranked pipeline.

## Consequences

- Heavy reranker deps are lazy and optional (`ml` for the cross-encoder,
  `cohere` extra for Cohere); construction never imports them, so the registry
  resolves the default and CI runs without the model. The fake (lexical) and
  LLM rerankers cover the offline/deterministic test paths.
- Exit (measured, logged): reranking an over-fetched hybrid candidate set lifts
  precision@1 from 0.8 (Phase 5 hybrid baseline) to 1.0 on the labeled set —
  `tests/test_rerank_eval.py`.
