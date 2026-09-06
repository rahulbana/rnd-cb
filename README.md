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

## Status — Phase 1: Foundations & core architecture skeleton ✅

A fully wired, empty system: every later phase adds an adapter instead of
inventing structure.

| Deliverable | Where |
|---|---|
| Repo scaffold (backend / frontend / infra / docs) | this tree |
| All port Protocols | `backend/app/domain/interfaces/` |
| Pydantic Settings + registry/factory | `backend/app/core/{config,registry}.py` |
| FastAPI skeleton (health, `/api/v1`, structured logging, global errors) | `backend/app/main.py`, `backend/app/api/` |
| Postgres schema v1 + Alembic migrations | `backend/app/db/` |
| Docker Compose (api, worker, Postgres, Redis, Chroma) | `infra/docker-compose.yml` |
| CI (ruff, mypy, pytest) | `.github/workflows/ci.yml` |
| One fake adapter per port (two fake embedders) | `backend/app/adapters/*/` |

**Exit test (proven):** `docker compose up` boots a fully wired empty app, and
flipping one env var (`EMBEDDER_PROVIDER=fake` → `fake_hash`) swaps the embedder
implementation with no code change — see `backend/tests/test_registry_swap.py`.

Later phases (2–10) add real parsers, chunkers, embedders, vector stores,
hybrid retrieval, reranking, LLM generation, auth + the enterprise frontend,
admin/analytics/eval, and cloud deployment. See the build plan for details.

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
