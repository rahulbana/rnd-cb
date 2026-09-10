# AI Sentiment Analyzer

Analyze the **sentiment** and **emotion** of text — one message at a time or in
bulk from a CSV — and explore the results in an interactive dashboard.

Built with **FastAPI** (Python 3.12), **React** (Vite), and the **OpenAI** API.

---

## Features

- **Sentiment classification** — positive / negative / neutral / **mixed**
- **Sentiment score** — a float from `-1.0` (very negative) to `+1.0` (very positive)
- **Emotion detection** — dominant emotion plus a per-emotion breakdown
- **Confidence** — how sure the model is
- **Keyword extraction** — the salient terms driving the sentiment
- **Aspect breakdown** — what's mentioned positively vs. negatively
- **Batch analysis** — many texts at once (one per line)
- **CSV upload** — drag & drop a file of reviews
- **Results dashboard** — charts + a sortable table with aggregate stats

### Example

Input:

> "The product is excellent but delivery was very slow."

Output:

- **Overall:** Mixed
- **Positive:** Product quality
- **Negative:** Delivery speed
- **Sentiment:** 0.42

---

## Requirements

- **Python 3.12**
- **Node.js 18+** (with `npm`)
- An **OpenAI API key** (optional — see below)

> Without an API key the app still works using a built-in **lexicon-based
> fallback** engine, so you can try everything locally before adding a key.

---

## Quick start

```bash
# 1. Install everything (creates a Python 3.12 virtualenv + installs deps)
./setup.sh

# 2. (optional) Add your OpenAI key
#    Edit backend/.env and set OPENAI_API_KEY=sk-...

# 3. Run backend (:8000) + frontend (:5173)
./start.sh
```

Then open **http://localhost:5173**.

The backend API docs are available at **http://localhost:8000/docs**.

---

## Project structure

```
.
├── setup.sh                 # one-time setup (Python venv + npm install)
├── start.sh                 # runs backend + frontend together
├── sample_reviews.csv       # example CSV to try the upload feature
├── backend/
│   ├── requirements.txt
│   ├── .env.example         # copy to .env and add your key
│   └── app/
│       ├── main.py          # FastAPI app + CORS + health
│       ├── config.py        # settings from env / .env
│       ├── schemas.py       # Pydantic request/response models
│       ├── analyzer.py      # OpenAI + lexicon-fallback engines
│       ├── aggregate.py     # batch statistics for the dashboard
│       └── routers/
│           └── analysis.py  # /api/analyze, /batch, /csv
└── frontend/
    ├── vite.config.js       # dev server + /api proxy to :8000
    └── src/
        ├── App.jsx
        ├── lib/             # api client + formatting helpers
        └── components/      # SingleAnalyze, BatchAnalyze, Dashboard, ResultCard
```

---

## API

| Method | Endpoint            | Description                                   |
| ------ | ------------------- | --------------------------------------------- |
| GET    | `/api/health`       | Status + which engine is active               |
| POST   | `/api/analyze`      | Analyze one text: `{ "text": "..." }`         |
| POST   | `/api/analyze/batch`| Analyze many: `{ "texts": ["...", "..."] }`   |
| POST   | `/api/analyze/csv`  | Analyze an uploaded CSV (multipart `file`)    |

For CSV uploads, the column named `text` / `review` / `comment` / `content` /
`message` / `feedback` is used automatically; otherwise the first column is used.

Example:

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The product is excellent but delivery was very slow."}'
```

---

## Configuration

All backend settings live in `backend/.env` (created from `.env.example`):

| Variable         | Default                | Description                          |
| ---------------- | ---------------------- | ------------------------------------ |
| `OPENAI_API_KEY` | _(empty)_              | Enables OpenAI-powered analysis      |
| `OPENAI_MODEL`   | `gpt-4o-mini`          | Model used for analysis              |
| `CORS_ORIGINS`   | `http://localhost:5173`| Allowed frontend origins             |
| `MAX_BATCH_SIZE` | `200`                  | Max texts per batch / CSV            |

---

## Where this can go next

```
Customer Reviews  →  AI Analysis  →  Sentiment Dashboard  →  Trend Analysis
```

Persist results to a database, add time-series trend charts, tag by product or
channel, and set up alerting on sentiment dips.
