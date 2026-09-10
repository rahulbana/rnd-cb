# AI Resume/CV Generator

Turn raw career information into a polished, professionally-written resume and
download it as a styled PDF. Built with **Python + FastAPI**, **React (Vite)**,
and the **OpenAI** LLM using structured generation.

```
User Information  →  LLM (structured output)  →  Structured Resume  →  Template  →  PDF
```

## Features

- **Structured input** — personal info, education, experience, skills, projects, achievements
- **AI-generated content** — the LLM writes a professional summary, sharpens your
  bullet points, and groups your skills into sensible categories (never invents facts)
- **Structured generation** — OpenAI structured outputs are parsed straight into
  typed Pydantic models, so the resume shape is always valid
- **4 resume styles** — `modern`, `classic`, `minimal`, `creative`
- **Live HTML preview** that matches the PDF exactly
- **PDF generation** via Jinja2 templates + WeasyPrint
- **Works without an API key** — falls back to a deterministic local generator so
  the whole pipeline runs out of the box

## Requirements

- Python 3.12
- Node.js 18+ / npm
- (For PDF export) WeasyPrint system libraries — `setup.sh` detects and tells you
  how to install them if missing.

## Quick start

```bash
./setup.sh      # creates backend/.venv (Python 3.12), installs backend + frontend deps
# (optional) add your key:  echo "OPENAI_API_KEY=sk-..." >> backend/.env
./start.sh      # runs FastAPI on :8000 and Vite on :5173
```

Then open <http://localhost:5173>.

- API docs (Swagger): <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/health>

## Project layout

```
backend/
  app/
    main.py              FastAPI app + CORS
    config.py            env-based settings
    schemas.py           Pydantic models (single source of truth for the resume shape)
    routers/resume.py    /api routes: generate, preview-html, render-pdf
    services/llm.py      structured LLM generation + local fallback
    services/pdf.py      Jinja2 -> HTML -> PDF (WeasyPrint)
    templates/           resume.html + per-style CSS (styles/)
  requirements.txt
  .env.example
frontend/
  src/
    App.jsx              form, style picker, live preview, PDF download
    components/          reusable form controls
    lib/api.js           fetch client
  package.json
setup.sh                 environment setup (Python 3.12 venv)
start.sh                 run backend + frontend together
```

## API

| Method | Path                | Purpose                                          |
|--------|---------------------|--------------------------------------------------|
| GET    | `/api/health`       | Status + whether the LLM is configured           |
| GET    | `/api/styles`       | List of available resume styles                  |
| POST   | `/api/generate`     | Raw input → polished structured resume (LLM)     |
| POST   | `/api/preview-html` | Structured resume → rendered HTML (live preview) |
| POST   | `/api/render-pdf`   | Structured resume → downloadable PDF             |

### Example

```bash
curl -s http://localhost:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "input": {
      "personal": {"full_name": "Jordan Rivera", "title": "Software Engineer"},
      "skills": ["Python", "React", "AWS"],
      "experience": [{"company": "Acme", "role": "Engineer",
                      "highlights": ["built the billing service"]}]
    },
    "style": "modern",
    "tone": "impactful"
  }'
```

## How the AI part works

`services/llm.py` sends the user's information to the model and requests a
response that conforms exactly to the `Resume` Pydantic schema
(`client.beta.chat.completions.parse` with `response_format=Resume`). Because the
schema is the same model the API accepts, the parsed result drops straight into
the template step. The system prompt constrains the model to rephrase — never
fabricate — and to organize skills and write a summary.

If `OPENAI_API_KEY` is not set, `generate_resume` uses a local fallback that
categorizes skills and assembles a clean resume so the app is fully usable
offline.

## Configuration

`backend/.env` (created from `.env.example` by `setup.sh`):

| Variable          | Default         | Notes                                        |
|-------------------|-----------------|----------------------------------------------|
| `OPENAI_API_KEY`  | _(empty)_       | Enables AI rewriting; empty = local fallback |
| `OPENAI_MODEL`    | `gpt-4o-mini`   | Any model supporting structured outputs      |
| `OPENAI_BASE_URL` | _(unset)_       | For OpenAI-compatible endpoints              |
| `CORS_ORIGINS`    | localhost:5173  | Comma-separated allowed origins              |
