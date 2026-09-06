# ADR 0005 — Async ingestion architecture

- Status: Accepted
- Date: 2026-09-06
- Phase: 4

## Context

Ingestion (parse → chunk → embed → index) must not run on the request thread:
a 400-page PDF would time out the API. It must be durable, resumable,
observable mid-flight, retriable, and idempotent.

## Decision

Upload becomes a two-step, async flow:

1. `POST /api/v1/documents` stores the raw file, dedups by checksum, creates a
   `Document` (`pending`) and an `IngestionJob` (`queued`), enqueues the job via
   the **TaskQueue** port, and returns **202 + job_id** immediately.
2. A worker runs the job off-thread. `GET /api/v1/jobs/{id}` polls status;
   `GET /api/v1/jobs/{id}/stream` streams progress as Server-Sent Events.

**Durability lives in `IngestionJobRunner`, not in Celery.** Retry-with-backoff,
dead-lettering (status `failed` after `INGEST_MAX_ATTEMPTS`), per-stage progress
(parsing → chunking → embedding → indexing, written to the job row), and
idempotent re-runs (prior chunks + their vectors are cleared before
re-indexing) all live in the runner. Celery and the inline queue are thin
callers, so the semantics are identical regardless of queue adapter.

TaskQueue adapters:

- **celery** (default) — enqueues on Redis; a separate worker container
  processes jobs. The API returns without blocking.
- **inline** — runs the job in-process during `enqueue`. No Redis/worker;
  ideal for local dev and deterministic tests.
- **fake** — records the job without running it (used to prove the API is
  non-blocking).

Also: **bulk upload** (`POST /api/v1/documents/bulk`, a zip of documents) and a
simple in-process **ingestion rate limiter** (`INGEST_RATE_LIMIT`), returning
429/413 when exceeded. In compose, api and worker share an `objectdata` volume
so the worker reads what the API stored (a shared object store replaces this in
Phase 10).

## Consequences

- The async worker resolves its ports from the **registry**, not from request-
  injected dependencies, so tests configure the registry (via settings + the
  app's engine) exactly as the worker sees it.
- Exit tests: 50 mixed-format documents upload without blocking (fake queue),
  then all drain to completion; an induced embedding failure retries and
  recovers, and a permanent failure dead-letters — `tests/test_jobs_api.py`,
  `tests/test_ingest_runner.py`.
- `TaskQueue.enqueue` is async so an inline adapter can await the work while
  Celery returns as soon as the job is queued.
