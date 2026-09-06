# ADR 0010 — Admin, analytics, observability & evaluation

- Status: Accepted
- Date: 2026-09-06
- Phase: 9

## Context

Operators need visibility into the running system, and the RAG pipeline needs a
scorecard that catches regressions before users do — plus every answer must be
explainable in one trace.

## Decision

**Admin dashboard** (admin-only): users, API keys, an ingestion **queue
monitor** (job counts by status/stage), per-document **reprocess**
(re-enqueues an idempotent ingestion job) and delete, and an active-provider
viewer (the live wiring diagram).

**Analytics**: usage (conversations, messages, tokens), **token cost by
provider** (from the price table), **latency percentiles** (p50/p95/p99),
**top-retrieved documents** (from citation counts), and **thumbs up/down**
(a `feedback` endpoint feeds the counts).

**Observability**: a **Tracer** port with `noop` (default) and `otel`
(OpenTelemetry, lazy) adapters. Spans wrap the RAG pipeline
(`rag.retrieve`/`rag.rerank`/`rag.assemble`) carrying chunk ids, reranker
scores, and prompt version, and the worker's ingest job. A **RAG-specific trace
view** (`GET /messages/{id}/trace`) returns the exact retrieved chunks, their
reranker scores, provider, tokens, and prompt version — so a bad answer is
explained in one place. `prompt_version` is persisted on every assistant turn
(migration `0004`).

**Evaluation**: an **EvalHarness** port with a `heuristic` adapter (lexical,
deterministic proxies for faithfulness / answer relevancy / context
precision-recall — runs in CI) and a `ragas` adapter (LLM-judged, lazy/opt-in).
`POST /admin/eval/run` runs a golden Q&A set through the live pipeline and
returns a **pass/fail Scorecard** against `EVAL_THRESHOLD`.

**CI eval gate**: `.github/workflows/eval.yml` runs the `eval`-marked tests on
PRs that touch retrieval, reranking, prompts, or the eval harness (a deploy gate
Phase 10 wires into the pipeline).

## Consequences

- Tracer and eval adapters are lazy; the registry resolves the defaults (`noop`,
  `heuristic`) and CI runs without OpenTelemetry or RAGAS installed
  (`observability` and `ragas` extras add them).
- Exit: an eval run produces a graded scorecard with a threshold, and any answer
  traces to its exact retrieved chunks, reranker scores, and prompt version —
  `tests/test_admin_api.py::test_exit_scorecard_and_traceability`. (The heuristic
  harness legitimately flags the fake LLM's boilerplate as low-faithfulness —
  the gate discriminating, not a bug.)
