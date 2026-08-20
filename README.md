# 📚 Study Notes & Question Generator

An end-to-end web app for **students and parents**. Upload a document — PDF, Word
(`.docx`), PowerPoint (`.pptx`), plain text, **a scanned PDF, or a photo/scan
image** (`.png`, `.jpg`, …) — and get back:

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

| Layer     | Technology                              |
|-----------|-----------------------------------------|
| Backend   | Python, FastAPI, OpenAI                 |
| Parsing   | pypdf, python-docx, python-pptx         |
| OCR       | OpenAI vision model + PyMuPDF (scanned) |
| Frontend  | React (Vite)                            |
| Output    | Self-contained HTML file                |

### Scanned documents & images

Scanned PDFs have no embedded text layer, so ordinary extraction returns
nothing. The app detects this automatically: when a PDF yields little or no
text, its pages are rasterised with **PyMuPDF** and read by an **OpenAI vision
model** (OCR). Uploaded image files (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`,
`.bmp`, `.tiff`) are OCR'd the same way. No OS packages (e.g. Tesseract) are
required. Results that used OCR are flagged with a "Read via OCR" badge in the
UI and in the API response (`ocr_used: true`).

## Project layout

```
backend/          FastAPI service
  app/
    main.py             API endpoints (/api/generate, /api/health, ...)
    document_parser.py  Extract text from PDF/DOCX/PPTX/TXT (in memory)
    ocr.py              OCR scanned PDFs & images via OpenAI vision + PyMuPDF
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
| `OPENAI_VISION_MODEL`| `OPENAI_MODEL`| Vision model used for OCR                |
| `MAX_OCR_PAGES`     | `10`           | Max scanned pages OCR'd per document      |
| `OCR_DPI`           | `150`          | Rasterisation DPI for scanned PDF pages   |

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
`.docx`/`.pptx` or PDF.

Scanned/image-only PDFs and image uploads **are** supported via OCR (see above);
this requires `OPENAI_API_KEY` to be set. OCR quality depends on how legible the
scan is, and only the first `MAX_OCR_PAGES` pages are processed to bound cost.
