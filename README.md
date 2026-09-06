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

Later phases (4–10) add async ingestion, hybrid retrieval, reranking, LLM
generation, auth + the enterprise frontend, admin/analytics/eval, and cloud
deployment. See the build plan for details.

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
