from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import MeetingNotes, TranscriptRequest
from app.services import llm

app = FastAPI(title="AI Meeting Notes Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model": settings.openai_model, "configured": bool(settings.openai_api_key)}


@app.post("/api/upload")
async def upload(file: UploadFile) -> dict:
    """Accept a transcript file (.txt / .md) and return its text content."""
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text.")
    if not text.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    return {"filename": file.filename, "transcript": text}


@app.post("/api/generate", response_model=MeetingNotes)
def generate(request: TranscriptRequest) -> MeetingNotes:
    """Generate structured meeting notes from a transcript."""
    if not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty.")
    try:
        return llm.generate_notes(request.transcript, request.meeting_title)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - surface provider errors to the client
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}")
