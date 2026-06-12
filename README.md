# 🍌 Nano Banana Photo Editor

A simple photo/image editing web app powered by the **Gemini Nano Banana** image model
(`gemini-2.5-flash-image`). Upload a photo, describe an edit in plain English, and get
the result back in seconds — or generate brand-new images from a text prompt.

## Features

- **Photo editing** — upload, drag-and-drop, or paste an image, then describe any edit:
  "add a sunset sky", "remove the person on the left", "put a party hat on the cat"…
- **Quick-edit presets** — remove background, enhance, black & white, vintage,
  watercolor, anime style, restore old photo
- **Text-to-image generation** — create images from a prompt
- **Before/after comparison** and one-click **download**
- **Iterative editing** — feed a result back in as the new source and keep refining
- Zero npm dependencies — plain Node.js + vanilla JS frontend
- The API key stays server-side; the browser never sees it

## Getting started

Requires Node.js 18+.

1. Get a free Gemini API key at <https://aistudio.google.com/apikey>
2. Run the server:

   ```bash
   GEMINI_API_KEY=your-key-here npm start
   ```

3. Open <http://localhost:3000>

## Configuration

| Environment variable | Default                  | Description                          |
| -------------------- | ------------------------ | ------------------------------------ |
| `GEMINI_API_KEY`     | _(required)_             | Your Gemini API key                  |
| `GEMINI_IMAGE_MODEL` | `gemini-2.5-flash-image` | Image model to use (e.g. set to `gemini-3-pro-image-preview` for Nano Banana Pro) |
| `PORT`               | `3000`                   | HTTP port                            |

## How it works

```
Browser (public/)  ──JSON (prompt + base64 image)──▶  server.js  ──▶  Gemini API
        ◀──────────── edited image (base64) ─────────────┘
```

- `POST /api/edit` — body `{ prompt, image: { mimeType, data } }`; sends the prompt and
  image to Gemini's `generateContent` endpoint and returns the edited image.
- `POST /api/generate` — body `{ prompt }`; text-to-image generation.
- `GET /api/health` — reports the configured model and whether an API key is set.
