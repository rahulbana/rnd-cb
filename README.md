# 🌐 AI Translator

A multilingual translation application powered by an LLM. Translate text
between many languages with control over tone — **formal**, **casual**, or
**technical** — plus batch translation and a translation history.

```
English
   ↓
Hindi
   ↓
"How are you?"
"आप कैसे हैं?"
```

## Features

- **Source / target language** selection (17 languages + auto-detect)
- **Text translation** with a clean side-by-side view
- **Style control**: formal, casual, and technical translations
- **Language detection** ("auto" source language)
- **Batch translation** — one text per line, translated in a single request
- **Translation history** — recent translations, with clear-all

## Tech stack

- **Backend**: Python 3.12, FastAPI, OpenAI SDK
- **Frontend**: React 18 + Vite

## Prerequisites

- **Python 3.12**
- **Node.js 18+** (for the frontend)
- An **OpenAI API key**

## Quick start

```bash
# 1. One-time setup: creates a Python 3.12 virtualenv (.venv), installs
#    backend + frontend deps, and creates .env from .env.example
./setup.sh

# 2. Add your key
#    Edit .env and set OPENAI_API_KEY=sk-...

# 3. Run both backend and frontend
./start.sh
```

Then open:

- Frontend: <http://localhost:5173>
- API docs: <http://127.0.0.1:8000/docs>

## Configuration

Configuration is read from environment variables or a local `.env` file
(see `.env.example`):

| Variable         | Default        | Description                              |
| ---------------- | -------------- | ---------------------------------------- |
| `OPENAI_API_KEY` | —              | **Required.** Your OpenAI API key.       |
| `OPENAI_MODEL`   | `gpt-4o-mini`  | Model used for translation.              |
| `OPENAI_BASE_URL`| —              | Optional OpenAI-compatible base URL.     |
| `HISTORY_LIMIT`  | `200`          | Max translations kept in memory.         |
| `CORS_ORIGINS`   | localhost:5173 | Comma-separated allowed frontend origins.|

## API

| Method   | Endpoint                | Description                          |
| -------- | ----------------------- | ------------------------------------ |
| `GET`    | `/api/health`           | Health + model/key status            |
| `GET`    | `/api/metadata`         | Supported languages and styles       |
| `POST`   | `/api/translate`        | Translate a single text              |
| `POST`   | `/api/translate/batch`  | Translate a list of texts            |
| `GET`    | `/api/history`          | List recent translations             |
| `DELETE` | `/api/history`          | Clear the history                    |

### Example

```bash
curl -X POST http://127.0.0.1:8000/api/translate \
  -H 'Content-Type: application/json' \
  -d '{"text": "How are you?", "source_lang": "auto", "target_lang": "hi", "style": "casual"}'
```

```json
{
  "translated_text": "आप कैसे हैं?",
  "detected_source_lang": "en",
  "source_lang": "auto",
  "target_lang": "hi",
  "style": "casual"
}
```

## Project layout

```
.
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app & routes
│   │   ├── translator.py    # LLM prompt control & OpenAI calls
│   │   ├── languages.py     # supported languages & styles
│   │   ├── schemas.py       # request/response models
│   │   ├── history.py       # in-memory translation history
│   │   └── config.py        # settings from env/.env
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── components/      # Translate / Batch / History panels
│   └── package.json
├── setup.sh                 # create venv + install deps
├── start.sh                 # run backend + frontend
└── .env.example
```

## Notes

- The translation history is **in-memory** and resets when the backend
  restarts. Swap `HistoryStore` for a database if you need persistence.
- Prompts instruct the model to return **structured JSON** and to translate
  (never answer) the input, which keeps behavior predictable across languages
  and styles.
