# 🧩 Chunking Strategy Explorer

A small **FastAPI** web app for *understanding* how different text-chunking
strategies behave. Upload a document, pick a strategy from a dropdown, tune its
parameters, and hit **Chunk it** — the app shows you **every chunk** it produced
**and an impact analysis** so you can see, side by side, how each strategy
affects chunk size, uniformity, overlap redundancy, and how often it slices
through a word or a sentence.

This is the decision that quietly makes or breaks a RAG pipeline, and it's
usually invisible. This tool makes it visible.

---

## What it does

1. **Browse & select a file** (or paste text).
2. **Choose one chunking strategy** from the dropdown.
3. **Adjust parameters** (chunk size, overlap, sentences-per-chunk, …).
4. **Submit** → the document is chunked and you get:
   - **All chunks**, each labelled with its character length, estimated tokens,
     source offset, and how much it overlaps the previous chunk (highlighted).
   - **Impact metrics** that quantify the strategy's consequences.
   - A **chunk-size distribution histogram**.

## Chunking strategies

| Strategy | What it does | Good for |
|---|---|---|
| **Fixed-size (characters)** | Constant-length character windows with optional overlap. Structure-blind — will cut mid-word. | Baseline; uniform embedding inputs. |
| **Recursive character** | Breaks on the largest natural boundary that fits (paragraph → line → sentence → word → char). The common RAG default. | General-purpose; respects structure and a size cap. |
| **Sentence-based** | Groups N whole sentences per chunk; never splits a sentence. | Prose where complete thoughts matter. |
| **Paragraph-based** | Splits on blank lines. Preserves author structure exactly. | Well-structured documents; uneven sizes OK. |
| **Token-based (word approx.)** | Groups N whitespace tokens per chunk — a tokenizer-free stand-in for token budgeting. | Keeping chunks under a rough token limit. |
| **Semantic (OpenAI embeddings)** | Embeds each sentence and starts a new chunk where meaning shifts. *Requires `OPENAI_API_KEY`.* | Topically-coherent chunks. |

## Impact metrics explained

- **Avg / min / max chars & tokens per chunk** — sizing at a glance.
- **Size variability (CV)** — coefficient of variation of chunk sizes. Low =
  uniform chunks (good for consistent embeddings); high = variable.
- **Overlap redundancy %** — extra characters stored because of overlap,
  relative to the source. A direct proxy for added storage/embedding cost.
- **Chunks cutting a word / sentence %** — how often a boundary lands in the
  middle of a word or sentence. This is where fixed-size splitting loses to
  structure-aware strategies, and the tool shows it numerically.
- **Source coverage %** — sanity check that chunks cover the document.

## Running it

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) enable the semantic strategy
export OPENAI_API_KEY=sk-...

# 3. Start the server
uvicorn app.main:app --reload

# 4. Open http://127.0.0.1:8000
```

The **semantic** strategy is the only one that calls OpenAI. Without a key it is
shown as disabled in the dropdown; every other strategy runs fully offline.

## Project layout

```
app/
  main.py            FastAPI app: routes, upload handling, param coercion
  chunkers.py        The six chunking strategies + strategy registry
  stats.py           Impact analysis (sizing, overlap, boundary cuts, histogram)
  templates/
    index.html       Single-page UI
  static/
    styles.css       Styling
    app.js           Dropdown, dynamic params, submit, results rendering
requirements.txt
```

## API

- `GET /` — the web UI.
- `GET /api/strategies` — strategy metadata (keys, params, availability).
- `POST /api/chunk` — multipart form: `strategy`, `params` (JSON), and either a
  `file` upload or a `text` field. Returns chunks + impact stats as JSON.
- `GET /healthz` — health check.

Uploads are capped at 2 MB and decoded as UTF-8 (with UTF-16 / Latin-1
fallback).
