"""FastAPI backend for the AI Email Writer.

Exposes a small set of endpoints that turn user intent into emails and
transform existing ones, all backed by an OpenAI chat model asked to return
structured JSON.
"""
from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field

import prompts

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

# The client reads OPENAI_API_KEY from the environment. We create it lazily so
# the server can still boot (and serve /health and /api/options) without a key.
_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is not set. Copy backend/.env.example to "
                "backend/.env and add your key, then restart the server.",
            )
        _client = OpenAI()
    return _client


app = FastAPI(title="AI Email Writer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    intent: str = Field(..., min_length=1, description="What the email should accomplish.")
    email_type: str = "general"
    tone: str = "professional"
    style: str = "professional"
    recipient: str | None = None
    sender: str | None = None


class RewriteRequest(BaseModel):
    body: str = Field(..., min_length=1)
    tone: str = "professional"
    style: str = "professional"
    instruction: str | None = None


class TransformRequest(BaseModel):
    body: str = Field(..., min_length=1)
    transform: str = Field(..., description="One of: shorten, expand.")
    subject: str | None = None


class EmailResponse(BaseModel):
    subject: str
    body: str


# ---------------------------------------------------------------------------
# Core helper: call the model and parse its JSON reply.
# ---------------------------------------------------------------------------


def _generate_email(user_prompt: str) -> EmailResponse:
    client = get_client()
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            temperature=0.7,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompts.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except OpenAIError as exc:  # network, auth, rate limit, etc.
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {exc}")

    raw = completion.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502, detail="Model returned a response that was not valid JSON."
        )

    return EmailResponse(
        subject=str(data.get("subject", "")).strip(),
        body=str(data.get("body", "")).strip(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL, "key_configured": bool(os.getenv("OPENAI_API_KEY"))}


@app.get("/api/options")
def options() -> dict:
    """Vocabularies the frontend uses to populate its dropdowns."""
    return {
        "email_types": prompts.EMAIL_TYPES,
        "tones": prompts.TONES,
        "styles": prompts.STYLES,
        "transforms": prompts.TRANSFORMS,
    }


@app.post("/api/generate", response_model=EmailResponse)
def generate(req: GenerateRequest) -> EmailResponse:
    prompt = prompts.build_generate_prompt(
        intent=req.intent,
        email_type=req.email_type,
        tone=req.tone,
        style=req.style,
        recipient=req.recipient,
        sender=req.sender,
    )
    return _generate_email(prompt)


@app.post("/api/rewrite", response_model=EmailResponse)
def rewrite(req: RewriteRequest) -> EmailResponse:
    prompt = prompts.build_rewrite_prompt(
        body=req.body,
        tone=req.tone,
        style=req.style,
        instruction=req.instruction,
    )
    return _generate_email(prompt)


@app.post("/api/transform", response_model=EmailResponse)
def transform(req: TransformRequest) -> EmailResponse:
    if req.transform not in prompts.TRANSFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown transform '{req.transform}'. Use one of: "
            f"{', '.join(prompts.TRANSFORMS)}.",
        )
    prompt = prompts.build_transform_prompt(
        body=req.body, transform=req.transform, subject=req.subject
    )
    return _generate_email(prompt)
