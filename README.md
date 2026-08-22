# YouTube Research Assistant

Paste a YouTube URL and the app fetches the video's transcript, then uses an
OpenAI model to:

- **Summarize** the video (TL;DR + key points + takeaways)
- **Answer questions** about it, grounded in the transcript
- **Generate a mind map** (rendered as a Mermaid diagram)

Built with **FastAPI** (Python) on the backend and **React + Vite** on the
frontend. Transcripts come from YouTube's own captions via
[`youtube-transcript-api`](https://pypi.org/project/youtube-transcript-api/) —
no audio download required. The OpenAI API key lives only on the server.

```
┌──────────────┐      /api/summary /api/ask /api/mindmap      ┌──────────────┐
│  React (Vite)│  ───────────────────────────────────────►   │   FastAPI    │
│   frontend   │                                              │   backend    │
└──────────────┘                                              └──────┬───────┘
                                                                     │
                                        youtube-transcript-api ◄─────┤
                                              OpenAI API      ◄───────┘
```

## Features

| Feature   | Endpoint         | Notes                                                |
| --------- | ---------------- | ---------------------------------------------------- |
| Transcript| `POST /api/transcript` | Resolves URL → caption text + title/thumbnail   |
| Summary   | `POST /api/summary`    | Structured Markdown summary                      |
| Q&A       | `POST /api/ask`        | Answers grounded in the transcript              |
| Mind map  | `POST /api/mindmap`    | Returns Mermaid `mindmap` source                |
| Health    | `GET /api/health`      | Reports model + whether the key is configured   |

Transcripts are cached in memory per video id, so summary / Q&A / mind-map calls
for the same video don't re-fetch captions.

## Prerequisites

- Python 3.10+
- Node.js 18+
- An OpenAI API key

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit .env and add your OPENAI_API_KEY

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

### Environment variables (`backend/.env`)

| Variable         | Required | Default          | Description                          |
| ---------------- | -------- | ---------------- | ------------------------------------ |
| `OPENAI_API_KEY` | yes      | —                | Your OpenAI key                      |
| `OPENAI_MODEL`   | no       | `gpt-4o-mini`    | Any chat-completions model           |
| `CORS_ORIGINS`   | no       | localhost:5173   | Comma-separated allowed frontend URLs|

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to the backend
on port 8000, so no extra configuration is needed. Paste a YouTube URL, click
**Load video**, then use the **Summary**, **Q&A**, and **Mind Map** tabs.

For a production build: `npm run build` (output in `frontend/dist`). Point it at
a deployed backend with `VITE_API_BASE=https://your-api-host` at build time.

## Notes

- The video must have captions available; videos without captions can't be
  analyzed. (You could extend the backend to transcribe audio with Whisper as a
  fallback.)
- Long transcripts are trimmed to a character budget before being sent to the
  model to keep requests fast and inexpensive.
- Network access to `youtube.com` is required for transcript fetching.
