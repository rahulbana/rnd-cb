# 🍌 Nano Banana Photo Editor

A simple photo/image editing web app powered by the **Gemini Nano Banana** image model
(`gemini-2.5-flash-image`), built with a **FastAPI** backend and a **React** (Vite) frontend.
Upload a photo, describe an edit in plain English, and get the result back in seconds —
or generate brand-new images from a text prompt.

## Features

- **Photo editing** — upload, drag-and-drop, or paste an image, then describe any edit:
  "add a sunset sky", "remove the person on the left", "put a party hat on the cat"…
- **Quick-edit presets** — remove background, enhance, black & white, vintage,
  watercolor, anime style, restore old photo
- **Text-to-image generation** — create images from a prompt
- **Before/after comparison** and one-click **download**
- **Iterative editing** — feed a result back in as the new source and keep refining
- The API key stays server-side; the browser never sees it

## Project structure

```
backend/    FastAPI app (proxies requests to the Gemini API, serves the built frontend)
frontend/   React + Vite app (UI)
```

## Getting started

Requires Python 3.10+ and Node.js 18+.

1. Get a free Gemini API key at <https://aistudio.google.com/apikey>

2. Install backend dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

3. Build the frontend:

   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

4. Run the server:

   ```bash
   GEMINI_API_KEY=your-key-here uvicorn backend.main:app --port 8000
   ```

5. Open <http://localhost:8000>

## Development mode

For frontend hot reload, run both servers and use the Vite dev server
(it proxies `/api` calls to FastAPI on port 8000):

```bash
# Terminal 1 — backend
GEMINI_API_KEY=your-key uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend with hot reload
cd frontend && npm run dev   # → http://localhost:5173
```

## Configuration

| Environment variable | Default                  | Description                          |
| -------------------- | ------------------------ | ------------------------------------ |
| `GEMINI_API_KEY`     | _(required)_             | Your Gemini API key                  |
| `GEMINI_IMAGE_MODEL` | `gemini-2.5-flash-image` | Image model to use (e.g. set to `gemini-3-pro-image-preview` for Nano Banana Pro) |

## API

- `POST /api/edit` — body `{ prompt, image: { mimeType, data } }`; sends the prompt and
  base64 image to Gemini's `generateContent` endpoint and returns the edited image.
- `POST /api/generate` — body `{ prompt }`; text-to-image generation.
- `GET /api/health` — reports the configured model and whether an API key is set.

```
React (frontend/)  ──JSON (prompt + base64 image)──▶  FastAPI (backend/)  ──▶  Gemini API
        ◀──────────── edited image (base64) ──────────────────┘
```
