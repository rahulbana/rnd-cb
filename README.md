# Intelligent RAG Chatbot

A production-shaped Retrieval-Augmented-Generation chatbot that ingests **any**
common document format, indexes it with a switchable retrieval pipeline, and
answers questions with **streaming** responses while showing **each processing
step live** in the UI.

- **Backend:** Python · FastAPI · WebSockets
- **Frontend:** React (Vite)
- **LLM:** OpenAI (default) · Ollama (local fallback) — switchable
- **Embeddings:** SentenceTransformers — pluggable
- **Vector store:** ChromaDB — pluggable
- **Retrieval:** `simple` (dense) or `hybrid` (dense + BM25, RRF-fused) — switchable
- **Re-ranking:** cross-encoder(s), on/off and chainable — switchable

---

## Supported formats & parsers

| Format | Extensions | Parser(s) |
|---|---|---|
| Text | `.txt .md .log` + pasted text | built-in |
| CSV / TSV | `.csv .tsv` | pandas |
| Excel | `.xlsx .xls .xlsm` | pandas + openpyxl |
| PDF | `.pdf` | **PyMuPDF** (default) · **pdfplumber** (tables) · **Unstructured** · **Docling** — with **pytesseract OCR fallback** for scanned pages |
| Word | `.docx .doc` | python-docx |
| PowerPoint | `.pptx .ppt` | python-pptx |
| Image | `.png .jpg .jpeg .webp .tiff .bmp` | **pytesseract** (OCR) |

Every parser normalizes its output to a list of typed `Element`s (title, text,
table, row, ocr, …) with provenance metadata (page, sheet, slide), so chunking
and citation work uniformly across formats.

---

## Architecture

```
Upload ──► Parse ──► Chunk ──► Embed ──► Index (ChromaDB)
 (per-format parser)  (structure-aware,   (SentenceTransformers)
                       token-budgeted)

Ask ──► Embed query ──► Retrieve ──► Re-rank ──► Generate (LLM, streamed)
                     (simple|hybrid) (cross-encoder,   │
                                       optional)        └─► tokens streamed
                                                            over WebSocket
```

Every stage emits `step` events over a WebSocket so the frontend renders a live
timeline; the answer streams token-by-token, and the grounding passages (with
scores) are surfaced as clickable citations.

### Chunking strategy

The default `recursive` strategy is **structure-aware and token-budgeted**: it
packs document elements in order up to a token budget (default 512) with a
sentence-aware overlap (default 64), never splitting atomic elements (tables,
CSV rows) mid-record, and recursively splitting oversized prose on
paragraph → line → sentence → word boundaries. Also available: `by_element`
(one chunk per element, ideal for dense tabular data) and `semantic`
(embedding-drift boundaries).

### Key extension points (all behind interfaces)

| Concern | Interface | Swap by |
|---|---|---|
| Embeddings | `embeddings/base.py` | implement `BaseEmbedder`, wire in `embeddings/__init__.py` |
| Vector store | `vectorstore/base.py` | implement `BaseVectorStore` |
| Retrieval | `retrieval/base.py` | implement `BaseRetriever` |
| Re-ranker | `reranking/base.py` | implement `BaseReranker` |
| LLM | `llm/base.py` | implement `BaseLLM` |
| Parser | `ingestion/parsers/base.py` | implement `BaseParser`, register in `ingestion/router.py` |

---

## Running locally

### Prerequisites
- Python 3.11+
- Node 18+
- **Tesseract OCR** binary (only for image / scanned-PDF OCR):
  `sudo apt-get install tesseract-ocr` or `brew install tesseract`

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set RAG_OPENAI_API_KEY=sk-...   (or use Ollama, see below)

uvicorn app.main:app --reload --port 8000
```

First run downloads the embedding + re-ranker models (a few hundred MB).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (proxies /api and /ws to :8000)
```

Open http://localhost:5173, drop in a document, watch the ingestion steps, then
ask questions.

### Using Ollama instead of OpenAI (fully local, no API key)

```bash
ollama pull llama3.1
# in backend/.env:
RAG_LLM_PROVIDER=ollama
RAG_OLLAMA_MODEL=llama3.1
```

The provider is also switchable live from the UI's **Retrieval settings** panel.

---

## Configuration

All settings are environment variables prefixed `RAG_` (see
[`backend/.env.example`](backend/.env.example)). Highlights:

| Variable | Default | Purpose |
|---|---|---|
| `RAG_LLM_PROVIDER` | `openai` | `openai` \| `ollama` |
| `RAG_RETRIEVAL_STRATEGY` | `hybrid` | `simple` \| `hybrid` |
| `RAG_RERANK_ENABLED` | `true` | toggle cross-encoder re-ranking |
| `RAG_RERANK_MODELS` | ms-marco-MiniLM | comma-separated, chained |
| `RAG_PDF_BACKEND` | `pymupdf` | `pymupdf` \| `pdfplumber` \| `unstructured` \| `docling` |
| `RAG_CHUNK_STRATEGY` | `recursive` | `recursive` \| `by_element` \| `semantic` |
| `RAG_EMBEDDING_MODEL` | all-MiniLM-L6-v2 | any SentenceTransformers model |

> `unstructured` and `docling` are heavy; they're commented out in
> `requirements.txt`. Uncomment to enable those PDF backends.

---

## API surface

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | liveness |
| `GET` | `/api/config` | effective config + switch options |
| `POST` | `/api/upload` | upload a file → `{ job_id }` |
| `POST` | `/api/text` | index pasted text → `{ job_id }` |
| `GET` | `/api/sources` | list indexed documents |
| `DELETE` | `/api/sources/{source}` | remove a document |
| `WS` | `/ws/ingest/{job_id}` | stream ingestion step events |
| `WS` | `/ws/chat` | send `{query, options}`, stream step/token/source events |

### WebSocket event shape

```jsonc
{ "type": "step",   "phase": "chat", "step": "retrieve", "status": "done", "detail": "20 candidates" }
{ "type": "sources", "data": [ { "n": 1, "source": "…", "score": 0.82, "preview": "…" } ] }
{ "type": "token",  "data": "partial answer text " }
{ "type": "done" }
{ "type": "error",  "detail": "…" }
```

---

## Notes on production-readiness

- **Interfaces everywhere** so ChromaDB / SentenceTransformers / OpenAI can each
  be replaced without touching the pipeline.
- **Lazy imports** for heavy/optional libraries — the API boots fast and only
  fails loudly if an unconfigured backend is actually invoked.
- **In-memory event bus** for streaming. For multi-worker/horizontal scaling,
  swap `EventBus` (in `core/events.py`) for a Redis/NATS-backed implementation
  behind the same interface, and move `PENDING_JOBS` to shared storage.
- Answers are **grounded and cited** — the model is instructed to answer only
  from retrieved context and cite passages `[n]`.
