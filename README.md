# Multi-Document Enterprise RAG Platform

A retrieval-augmented generation system where every moving part — parser,
chunker, embedder, vector store, reranker, retriever, and LLM — is a
**swappable adapter behind a fixed interface**. Built with Python, FastAPI,
and React; shipped first on Docker, then GCP Cloud Run, without a rewrite in
between.

The technique is Ports & Adapters (hexagonal architecture): every capability
with more than one reasonable implementation is a Python `Protocol` (a
**port**); concrete providers (**adapters**) implement it; a **registry**
driven by environment variables resolves which adapter runs at runtime. Business
logic imports the interface, never a provider SDK.

## Status

### Phase 1 — Foundations & core architecture skeleton ✅

A fully wired, empty system: every later phase adds an adapter instead of
inventing structure. Ports for all nine capabilities; a config-driven registry;
FastAPI skeleton (health, `/api/v1`, structured logging, global errors);
Postgres schema v1 + Alembic; Docker Compose (api, worker, Postgres, Redis,
Chroma); CI. **Exit (proven):** flipping `EMBEDDER_PROVIDER=fake → fake_hash`
swaps the implementation with no code change — `backend/tests/test_registry_swap.py`.

### Phase 2 — Multi-format document ingestion (synchronous path) ✅

Turn any uploaded file into the same canonical `ParsedDocument`.

| Deliverable | Where |
|---|---|
| Parser registry keyed by MIME + fallback chain | `backend/app/adapters/parsers/router.py` |
| Parser adapters (plain/md, PyMuPDF, DOCX, Docling, Unstructured) | `backend/app/adapters/parsers/` |
| OCR path for scanned images (Tesseract; Docling in prod) | `backend/app/adapters/parsers/image_parser.py` |
| Object storage abstraction (local-disk adapter) | `backend/app/adapters/storage/local_disk.py` |
| Upload endpoint with checksum-based dedup | `backend/app/api/v1/routes/documents.py` |
| Fixture-based tests per format | `backend/tests/test_parsers.py`, `test_upload.py` |

**Exit (proven):** a PDF, a DOCX, a scanned PNG, and a Markdown file all upload
via `POST /api/v1/documents` and return the same structured representation —
`backend/tests/test_upload.py::test_exit_all_formats_return_same_shape`.

### Phase 3 — Chunking, embedding & vector storage ✅

Wire parsed documents into a searchable vector index; embedder and vector store
both fully swappable.

| Deliverable | Where |
|---|---|
| Chunkers: structure-aware (default), fixed-size, recursive | `backend/app/adapters/chunkers/` |
| Embedders: Sentence-Transformers (local), OpenAI | `backend/app/adapters/embedders/` |
| Vector stores: Chroma (default), Postgres+pgvector | `backend/app/adapters/vector_stores/` |
| Namespace/collection per org (multi-tenancy hook) | store `namespace` arg |
| `ingestion_service` (parser → chunker → embedder → store) | `backend/app/services/ingestion_service.py` |
| Raw similarity search endpoint | `POST /api/v1/documents/search` |

**Exit (proven):** a document ingests end-to-end and is retrievable by raw
similarity search; switching `VECTOR_STORE_PROVIDER` chroma ↔ pgvector is zero
code change — `backend/tests/test_vector_store_swap.py`,
`backend/tests/test_ingestion.py`.

### Phase 4 — Async ingestion architecture ✅

Ingestion runs off the request thread: durable, resumable, observable, retriable.

| Deliverable | Where |
|---|---|
| Celery + Redis broker/backend, separate worker container | `backend/app/workers/`, `infra/docker-compose.yml` |
| Upload returns `job_id`; status + SSE progress | `POST /api/v1/documents` (202), `GET /api/v1/jobs/{id}[/stream]` |
| Per-stage progress (parsing/chunking/embedding/indexing) | `backend/app/workers/ingest_runner.py` |
| Retry w/ backoff, dead-letter, idempotent re-runs | `IngestionJobRunner` |
| Bulk upload (zip) + ingestion rate limiting | `POST /api/v1/documents/bulk`, `backend/app/core/ratelimit.py` |
| TaskQueue port (celery / inline / fake adapters) | `backend/app/adapters/task_queues/` |

**Exit (proven):** 50 mixed-format documents upload concurrently without
blocking the API, then all process to completion; an induced worker failure
retries and recovers (and a permanent one dead-letters) —
`backend/tests/test_jobs_api.py`, `backend/tests/test_ingest_runner.py`.

### Phase 5 — Hybrid retrieval & query understanding ✅

Retrieve independent of generation, combining dense and lexical search so
quality can be measured on its own.

| Deliverable | Where |
|---|---|
| Dense / sparse (BM25) / hybrid (RRF) retrievers | `backend/app/adapters/retrievers/` |
| Query preprocessing: rewriting + metadata-filter extraction (year, doc type) | `backend/app/services/query_understanding.py` |
| Per-document / per-collection retrieval scoping | `Retriever.retrieve(document_ids=…)` |
| Standalone `/retrieve` endpoint (no generation) | `POST /api/v1/retrieve` |
| Retrieval eval harness (recall@k, MRR) | `backend/app/evaluation/retrieval_eval.py` |

**Exit (measured, logged):** on a 12-doc corpus with a 5-query labeled set,
hybrid retrieval beats the dense-only baseline (recall@3 **1.0** vs **0.2**) —
`backend/tests/test_retrieval_eval.py`.

### Phase 6 — Reranking & context assembly ✅

Push the truly relevant chunks to the top and pack them into a token-budgeted,
citation-tagged context.

| Deliverable | Where |
|---|---|
| Rerankers: cross-encoder (default), Cohere, LLM-as-reranker | `backend/app/adapters/rerankers/` |
| MMR diversity pass + near-duplicate dedup | `backend/app/services/context_assembly.py` |
| Token-budget-aware context packing (injected tokenizer) | `ContextAssembler` |
| Citation tagging (chunk → document + page) | `ContextAssembler` |
| Optional contextual compression | `ContextAssembler(compress=True)` |

**Exit (measured, logged):** reranking an over-fetched hybrid candidate set
lifts precision@1 from **0.8** (Phase 5 baseline) to **1.0** on the labeled set
— `backend/tests/test_rerank_eval.py`.

### Phase 7 — LLM orchestration & RAG generation ✅

Grounded, cited, streamed answers from any of four LLM backends interchangeably.

| Deliverable | Where |
|---|---|
| LLM adapters: Ollama (default), OpenAI, Anthropic, Gemini | `backend/app/adapters/llm_providers/` |
| Versioned Jinja2 prompts (grounded + citation-format system prompt) | `backend/app/prompts/` |
| Streaming generation over SSE | `POST /api/v1/chat/stream` |
| Conversation memory (sliding window + summarization), persisted | `backend/app/services/conversation_memory.py` |
| Prompt-injection defenses + explicit "not found" fallback | `backend/app/services/prompt_safety.py`, `ChatService` |
| Per-request cost/latency/token logging | `backend/app/services/cost.py`, `ChatService` |

**Exit (proven):** the same query streams a cited answer, and one env var
(`LLM_PROVIDER`) selects Ollama / OpenAI / Anthropic / Gemini at an identical
call site — `backend/tests/test_chat_swap.py`, `backend/tests/test_llm_providers.py`.

### Phase 8 — Auth, API hardening & enterprise frontend core ✅

Turn the API into something a real user logs into, and ship the first working
slice of the enterprise React app.

| Deliverable | Where |
|---|---|
| JWT auth (register/login/refresh), Argon2id, API-key auth | `backend/app/core/security.py`, `backend/app/api/v1/routes/auth.py` |
| RBAC (admin/user), login rate limiting, ownership checks | `backend/app/api/v1/deps_auth.py` |
| org_id/owner_id enforced on every data route | documents / jobs / retrieve / chat |
| React + TS + Vite + Tailwind, React Query + Zustand | `frontend/src/` |
| Auth flow (login/register, JWT storage + refresh, protected routing) | `frontend/src/features/auth/`, `frontend/src/store/auth.ts` |
| Chat UI (streaming + inline citations), conversation sidebar | `frontend/src/features/chat/` |
| Document manager (upload with live progress, list, delete, status) | `frontend/src/features/documents/` |

**Exit (proven via API-level journey test):** a user registers, logs in, bulk-
uploads a mixed batch, watches ingestion reach completion, and holds a streamed,
cited conversation — `backend/tests/test_user_journey.py`. The frontend
typechecks and builds (`npm run build`).

### Phase 9 — Admin, analytics, observability & evaluation ✅

Give operators visibility and give the RAG pipeline a scorecard.

| Deliverable | Where |
|---|---|
| Admin dashboard (users, API keys, queue monitor, reprocess/delete, provider viewer) | `backend/app/api/v1/routes/admin.py`, `frontend/src/features/admin/` |
| Analytics (usage, cost by provider, latency percentiles, top docs, 👍/👎) | `backend/app/services/analytics_service.py` |
| OpenTelemetry tracing (API + worker) + RAG trace view | `Tracer` port, `GET /messages/{id}/trace` |
| RAGAS/heuristic eval harness (faithfulness, relevancy, context precision/recall) | `backend/app/adapters/eval_harnesses/` |
| CI eval gate on retrieval/prompt changes | `.github/workflows/eval.yml` |

**Exit (proven):** an eval run produces a pass/fail scorecard with a threshold,
and any answer traces to its exact retrieved chunks, reranker scores, and prompt
version — `backend/tests/test_admin_api.py::test_exit_scorecard_and_traceability`.

Later phase (10) adds production hardening and Cloud Run deployment. See the
build plan for details.

## Layout

```
backend/    FastAPI app, ports & adapters, services, workers, db, evaluation
frontend/   React + TS + Vite scaffold (full app: Phase 8)
infra/      docker-compose (+ Terraform for GCP: Phase 10)
docs/       ADRs and runbooks
```

## Run it

### With Docker Compose (recommended)

```bash
docker compose -f infra/docker-compose.yml up --build
```

- API: http://localhost:8080 (docs at `/docs`)
- Health: http://localhost:8080/api/v1/health
- Live wiring diagram: http://localhost:8080/api/v1/providers

The API container runs `alembic upgrade head` before serving, so the schema is
created on first boot.

### Backend locally

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --port 8080
```

### Checks

```bash
cd backend
ruff check . && ruff format --check .
mypy app
pytest -q
```

### Frontend locally

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Swapping an implementation

Change one value in `.env` and restart — no code change:

```env
EMBEDDER_PROVIDER=fake        # or fake_hash  (Phase 3: sentence_transformers | openai)
VECTOR_STORE_PROVIDER=fake    # (Phase 3: chroma | pgvector | pinecone)
LLM_PROVIDER=fake             # (Phase 7: ollama | openai | anthropic | gemini)
```

See `docs/adr/0001-ports-and-adapters.md` for the pattern and
`docs/runbooks/reindex-on-embedder-change.md` for the embedding-dimension-drift
guardrail.
