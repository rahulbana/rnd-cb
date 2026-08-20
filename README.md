# 📚 Study Notes & Question Generator

An end-to-end web app for **students and parents**. Upload a document — PDF, Word
(`.docx`), PowerPoint (`.pptx`), plain text, **a scanned PDF, or a photo/scan
image** (`.png`, `.jpg`, …) — and get back:

- **Detailed revision notes** — every sub-topic in the document is expanded into
  its own in-depth section (overview, multi-paragraph explanation, key points,
  worked examples, formulas), with a table of contents and, where helpful, a
  **reference diagram/image found online**, plus a glossary
- **Optional online research** — the app can search the web (via **DuckDuckGo**
  or **Tavily**) for curriculum-aligned reference material from reputable
  sources (education boards, coaching centres, educational sites) to enrich the
  notes and questions, with the sources cited in the downloads.
- **Depth of coverage** — pick *Standard*, *Thorough*, or *Exhaustive*
  ("topper mode"). Exhaustive generates a large question bank that tests every
  concept, including small, easily-overlooked facts. Questions are generated per
  type in concurrent calls, so large sets never get truncated.
- **Practice questions** with answers, in every requested format:
  - True / False
  - Multiple Choice (MCQ)
  - Fill in the Blanks
  - Very Short Answer
  - Short Answer
  - Long Answer
  - Case-Based
- **Previous Year Questions** — searches online for previous-year / board exam
  papers on the document's topic and compiles those questions (with model
  answers, and the year/exam/marks when the source states them, plus a link back
  to the source). Appears in the Questions downloads.

Everything can be viewed in the browser and downloaded as **three separate,
printable HTML files**:

1. **Notes** — study/revision notes only
2. **Questions + Answers** — the full question set with an answer key
3. **Questions only** — a clean practice/exam sheet (no answers, with space to
   write)

> **Privacy:** No documents or generated content are stored. Files are parsed in
> memory and discarded once the response is returned. Only the **extracted plain
> text** is sent to OpenAI — never the original file or its page images. Scanned
> files are OCR'd **locally** (Tesseract) before any text leaves the server.

## Tech stack

| Layer     | Technology                              |
|-----------|-----------------------------------------|
| Backend   | Python, FastAPI, OpenAI                 |
| Parsing   | pypdf, python-docx, python-pptx         |
| OCR       | Tesseract (local) + PyMuPDF (scanned)   |
| Frontend  | React (Vite)                            |
| Output    | Self-contained HTML file                |

### Text-first pipeline

Text is always extracted **on the server first**, and only that text is sent to
OpenAI to generate notes and questions. The original document — and, for scanned
files, its page images — never leaves the server.

### Detailed notes with images

The notes are built in two stages: the document is first outlined into its
sub-topics, then each sub-topic is expanded in its own concurrent LLM call (so
long, detailed explanations are never truncated). When online research is on,
each section can be illustrated with a **reference image found via image search**
and embedded by URL, with a link back to its source. Images are hotlinked from
the web, so they render when the notes HTML is opened online; if a lookup fails
the section simply renders without an image. Turn images off with
`ENABLE_IMAGE_SEARCH=false`.

### Scanned documents & images

Scanned PDFs have no embedded text layer, so ordinary extraction returns
nothing. The app detects this automatically: when a PDF yields little or no
text, its pages are rasterised with **PyMuPDF** and read **locally** with
**Tesseract** (`pytesseract`). Uploaded image files (`.png`, `.jpg`, `.jpeg`,
`.webp`, `.gif`, `.bmp`, `.tiff`) are OCR'd the same way. Results that used OCR
are flagged with a "Read via OCR" badge in the UI and in the API response
(`ocr_used: true`).

**Requirement:** the Tesseract binary must be installed on the host:

```bash
# Debian/Ubuntu
sudo apt-get install -y tesseract-ocr
# macOS
brew install tesseract
```

`GET /api/health` reports `ocr_available` so you can confirm it's set up. For
non-English scans, install the matching language pack and set `OCR_LANG`
(e.g. `eng+hin`).

## Project layout

```
backend/          FastAPI service
  app/
    main.py             API endpoints (/api/generate, /api/health, ...)
    document_parser.py  Extract text from PDF/DOCX/PPTX/TXT (in memory)
    ocr.py              Local OCR (Tesseract) for scanned PDFs & images
    web_research.py     Optional online reference research (DuckDuckGo / Tavily)
    llm.py              OpenAI prompt + JSON parsing
    html_generator.py   Render the 3 printable HTML files (notes / Q+A / Q-only)
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
| `DEFAULT_COVERAGE`  | `thorough`     | Default depth: standard/thorough/exhaustive|
| `MAX_QUESTIONS_PER_TYPE`| `40`       | Hard ceiling on questions per type        |
| `GENERATION_WORKERS`| `6`            | Concurrency for per-type generation calls |
| `NOTES_MAX_SECTIONS`| `14`           | Max sub-topics expanded into detailed notes|
| `NOTES_MAX_IMAGES`  | `6`            | Max online reference images embedded in notes|
| `ENABLE_IMAGE_SEARCH`| `true`        | Embed reference images in notes (DDG images)|
| `OCR_LANG`          | `eng`          | Tesseract language(s), e.g. `eng+hin`     |
| `MAX_OCR_PAGES`     | `20`           | Max scanned pages OCR'd per document      |
| `OCR_DPI`           | `300`          | Rasterisation DPI for scanned PDF pages   |
| `ENABLE_WEB_SEARCH` | `true`         | Turn online reference research on/off     |
| `SEARCH_PROVIDER`   | `duckduckgo`   | `duckduckgo` (no key) or `tavily`         |
| `TAVILY_API_KEY`    | *(empty)*      | Required when `SEARCH_PROVIDER=tavily`    |
| `RESEARCH_MAX_RESULTS`| `6`          | Search results fetched per document       |
| `RESEARCH_MAX_SOURCES`| `8`          | Max reference URLs cited                  |

## API

| Method | Path                    | Description                              |
|--------|-------------------------|------------------------------------------|
| GET    | `/api/health`           | Status + whether OpenAI key is set       |
| GET    | `/api/question-types`   | List of supported question types         |
| POST   | `/api/generate`         | Upload a file → JSON (material + 3 HTML files) |
| POST   | `/api/generate/html`    | Upload a file → one raw HTML document      |

`POST /api/generate` returns a `downloads` object with three self-contained HTML
documents: `notes`, `questions_with_answers`, and `questions_only`.

`POST /api/generate/html` takes an extra `variant` field (`notes` |
`questions_with_answers` | `questions_only`, default `questions_with_answers`)
and returns just that document.

`POST /api/generate` is `multipart/form-data`:

- `file`: the document
- `question_types`: comma-separated ids (e.g. `mcq,true_false,long`)
- `grade_level`: optional string (e.g. `Class 8`)
- `web_search`: `true`/`false` (default `true`) — gather online references
- `coverage`: `standard` | `thorough` | `exhaustive` (default `thorough`)
- `previous_year`: `true`/`false` (default `true`) — search online for
  previous-year / board exam papers and include those questions

The JSON response includes `web_search_used` and a `sources` list of the
reference URLs used.

### Online reference research

When `web_search` is on (and `ENABLE_WEB_SEARCH=true`), a short search query is
distilled from the extracted text and run against **DuckDuckGo** (default, no API
key) or **Tavily** (`SEARCH_PROVIDER=tavily` with `TAVILY_API_KEY`). The result
snippets and URLs are passed as *additional* context to notes/question
generation — the uploaded document stays the primary source — and the URLs are
cited in the Notes and Questions + Answers downloads. Only the short query
leaves the server, never the file. The step is best-effort: if search is
unavailable, generation proceeds normally without it.

## Notes on legacy formats

Old binary `.doc` and `.ppt` files are not readable by the pure-Python
libraries. The API returns a friendly message asking the user to re-save them as
`.docx`/`.pptx` or PDF.

Scanned/image-only PDFs and image uploads **are** supported via local OCR (see
above); this requires the Tesseract binary. OCR quality depends on how legible
the scan is, and only the first `MAX_OCR_PAGES` pages are processed to bound
work.
