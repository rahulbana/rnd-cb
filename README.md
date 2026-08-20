# 📚 Study Notes & Question Generator

An end-to-end web app for **students and parents**. Upload a document — PDF, Word
(`.docx`), PowerPoint (`.pptx`), or plain text — and get back:

- **Revision notes** (summary, key points, section-wise bullets, glossary)
- **Practice questions** with answers, in every requested format:
  - True / False
  - Multiple Choice (MCQ)
  - Fill in the Blanks
  - Very Short Answer
  - Short Answer
  - Long Answer
  - Case-Based

Everything can be viewed in the browser and **downloaded as a single, printable
HTML file** (answers are collapsible, so it doubles as a quiz sheet).

> **Privacy:** No documents or generated content are stored. Files are parsed in
> memory and discarded once the response is returned.

## Tech stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Python, FastAPI, OpenAI             |
| Parsing   | pypdf, python-docx, python-pptx     |
| Frontend  | React (Vite)                        |
| Output    | Self-contained HTML file            |

## Project layout

```
backend/          FastAPI service
  app/
    main.py             API endpoints (/api/generate, /api/health, ...)
    document_parser.py  Extract text from PDF/DOCX/PPTX/TXT (in memory)
    llm.py              OpenAI prompt + JSON parsing
    html_generator.py   Render notes + questions to a printable HTML file
    schemas.py          Pydantic models & question-type definitions
  requirements.txt
  .env.example
frontend/         React (Vite) single-page app
  src/App.jsx, Results.jsx, api.js, styles.css
```

## Getting started

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY=sk-...        # required
# optional: export OPENAI_MODEL=gpt-4o-mini

uvicorn app.main:app --reload --port 8000
```

Health check: <http://localhost:8000/api/health>

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. In dev, requests to `/api` are proxied to the
backend on port 8000 (see `vite.config.js`), so no CORS setup is needed.

## Configuration

Backend environment variables (see `backend/.env.example`):

| Variable            | Default        | Purpose                                  |
|---------------------|----------------|------------------------------------------|
| `OPENAI_API_KEY`    | *(required)*   | OpenAI authentication                    |
| `OPENAI_MODEL`      | `gpt-4o-mini`  | Model used for generation                |
| `ALLOWED_ORIGINS`   | `*`            | CORS origins (comma-separated)           |
| `MAX_UPLOAD_BYTES`  | `15728640`     | Upload size limit (15 MB)                |
| `MAX_SOURCE_CHARS`  | `48000`        | Max characters of source text sent to LLM|

## API

| Method | Path                    | Description                              |
|--------|-------------------------|------------------------------------------|
| GET    | `/api/health`           | Status + whether OpenAI key is set       |
| GET    | `/api/question-types`   | List of supported question types         |
| POST   | `/api/generate`         | Upload a file → JSON (material + HTML)    |
| POST   | `/api/generate/html`    | Upload a file → raw HTML document         |

`POST /api/generate` is `multipart/form-data`:

- `file`: the document
- `question_types`: comma-separated ids (e.g. `mcq,true_false,long`)
- `grade_level`: optional string (e.g. `Class 8`)

## Notes on legacy formats

Old binary `.doc` and `.ppt` files are not readable by the pure-Python
libraries. The API returns a friendly message asking the user to re-save them as
`.docx`/`.pptx` or PDF. Scanned/image-only PDFs (no text layer) are also not
supported.
