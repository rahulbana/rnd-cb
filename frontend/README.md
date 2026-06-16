# Book Review Aggregator — Frontend

React (Vite) UI for the multi-agent book review aggregator. Enter a book title
(and optional author), trigger the backend agent pipeline, and view the
summary, verification result, and reviews grouped by source type — with
one-click **Markdown** and **PDF** downloads.

## Setup

```bash
cd frontend
npm install
```

## Run (with the backend on :8000)

```bash
# terminal 1 — backend
cd ../backend && uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend
cd frontend && npm run dev          # http://localhost:5173
```

Vite proxies `/analyze` and `/export/*` to `http://localhost:8000` (see
`vite.config.js`), so no CORS setup is needed in dev. For a deployed backend,
set `VITE_API_BASE` (see `.env.example`).

## Structure

```
src/
  api.js                 # fetch wrapper: analyze + file download
  App.jsx                # state + layout
  components/
    SearchForm.jsx       # title/author input
    ReportView.jsx       # summary, verification banner, grouped reviews, download buttons
    ReviewCard.jsx       # single review (reviewer type, sentiment, excerpt)
  styles.css
```

> Authentication is intentionally not included yet (per project scope).
