"""Nano Banana Photo Editor — FastAPI backend.

Proxies image edit/generate requests to the Gemini API so the API key
never reaches the browser, and serves the built React frontend.
"""

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# "Nano Banana" is the nickname of Gemini's image generation/editing model.
MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app = FastAPI(title="Nano Banana Photo Editor")


class ImageData(BaseModel):
    mimeType: str
    data: str  # base64-encoded image bytes


class EditRequest(BaseModel):
    prompt: str = Field(min_length=1)
    image: ImageData


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)


async def call_gemini(parts: list[dict]) -> dict:
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "GEMINI_API_KEY is not set. Get a key at "
                "https://aistudio.google.com/apikey and restart the server with it."
            ),
        )

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            GEMINI_URL,
            headers={"x-goog-api-key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": parts}],
                "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
            },
        )

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.status_code != 200:
        message = data.get("error", {}).get("message") or (
            f"Gemini API error (HTTP {response.status_code})"
        )
        raise HTTPException(status_code=response.status_code, detail=message)

    candidates = data.get("candidates") or [{}]
    out_parts = candidates[0].get("content", {}).get("parts", [])
    image_part = next((p for p in out_parts if p.get("inlineData", {}).get("data")), None)
    text_part = next((p for p in out_parts if isinstance(p.get("text"), str)), None)

    if image_part is None:
        reason = candidates[0].get("finishReason")
        detail = (text_part or {}).get("text") or (
            f"Model returned no image (finish reason: {reason})"
            if reason
            else "Model returned no image"
        )
        raise HTTPException(status_code=502, detail=detail)

    return {
        "image": {
            "mimeType": image_part["inlineData"].get("mimeType", "image/png"),
            "data": image_part["inlineData"]["data"],
        },
        "text": (text_part or {}).get("text"),
    }


@app.get("/api/health")
async def health():
    return {"ok": True, "model": MODEL, "keyConfigured": bool(GEMINI_API_KEY)}


@app.post("/api/edit")
async def edit(req: EditRequest):
    parts = [
        {"text": req.prompt.strip()},
        {"inlineData": {"mimeType": req.image.mimeType, "data": req.image.data}},
    ]
    return await call_gemini(parts)


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    return await call_gemini([{"text": req.prompt.strip()}])


# Serve the built React frontend (run `npm run build` in frontend/ first).
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
