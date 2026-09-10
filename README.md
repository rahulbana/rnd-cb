# AI Resume Analyzer

Upload a PDF resume and get instant, AI-generated feedback: an overall score,
detected skills, missing skills, strengths, weaknesses, an experience
assessment, and concrete recommendations.

Built with **Python 3.12 + FastAPI** (backend), **React + Vite** (frontend),
and the **OpenAI** API for LLM analysis with structured JSON output.

## Features

- 📄 PDF resume upload (drag & drop or browse)
- 🔍 Resume text extraction (`pypdf`)
- 🧠 LLM analysis returning structured JSON
- 🛠️ Skills extraction & missing-skills detection
- 📊 Experience analysis (years, seniority, summary)
- ✅ Strengths / ⚠️ weaknesses
- 🎯 Overall score (0–100) and prioritized improvement suggestions

## Requirements

- Python **3.12**
- Node.js 18+ and npm
- An OpenAI API key

## Setup

```bash
./setup.sh
```

This will:

1. Create a Python 3.12 virtual environment at `backend/.venv`.
2. Install backend dependencies from `backend/requirements.txt`.
3. Install frontend dependencies (`npm install`).
4. Create `backend/.env` from the example.

> If your interpreter isn't named `python3.12`, run
> `PYTHON_BIN=/path/to/python3.12 ./setup.sh`.

Then add your OpenAI API key to `backend/.env`:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## Run

```bash
./start.sh
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs

The Vite dev server proxies `/api/*` to the FastAPI backend, so no CORS
configuration is needed for local development.

## API

### `POST /api/analyze`

Multipart form upload with a `file` field (PDF). Returns:

```json
{
  "filename": "resume.pdf",
  "characters_extracted": 3120,
  "analysis": {
    "overall_score": 78,
    "skills": ["Python", "FastAPI", "PostgreSQL", "React"],
    "missing_skills": ["Docker", "Kubernetes", "LLM Evaluation"],
    "strengths": ["..."],
    "weaknesses": ["..."],
    "experience": {
      "total_years": 5,
      "seniority_level": "Senior",
      "summary": "..."
    },
    "recommendations": [
      "Add measurable achievements",
      "Improve project descriptions",
      "Add GenAI experience"
    ]
  }
}
```

### `GET /api/health`

Returns service status and whether the LLM key is configured.

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app & routes
│   │   ├── config.py          # env-based settings
│   │   ├── models.py          # Pydantic response models
│   │   └── services/
│   │       ├── pdf.py         # PDF text extraction
│   │       └── analyzer.py    # OpenAI LLM analysis
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # upload UI
│   │   ├── Results.jsx        # feedback rendering
│   │   ├── api.js             # backend client
│   │   └── index.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── setup.sh
└── start.sh
```
