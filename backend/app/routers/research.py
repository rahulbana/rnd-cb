from fastapi import APIRouter, HTTPException

from ..schemas import (
    AskRequest,
    AskResponse,
    MindMapResponse,
    SummaryResponse,
    TranscriptResponse,
    VideoRequest,
)
from ..services import llm, youtube

router = APIRouter(prefix="/api", tags=["research"])


def _load(url: str) -> youtube.Transcript:
    """Resolve a request URL to a transcript, mapping errors to HTTP codes."""
    try:
        return youtube.get_transcript(url)
    except youtube.InvalidURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except youtube.TranscriptError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _meta(t: youtube.Transcript) -> dict:
    return {
        "video_id": t.video_id,
        "title": t.title,
        "author": t.author,
        "thumbnail_url": t.thumbnail_url,
    }


def _guard_llm(fn, *args):
    try:
        return fn(*args)
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/transcript", response_model=TranscriptResponse)
def get_transcript(req: VideoRequest) -> TranscriptResponse:
    t = _load(req.url)
    return TranscriptResponse(
        **_meta(t),
        transcript=t.text,
        language=t.language,
        char_count=len(t.text),
    )


@router.post("/summary", response_model=SummaryResponse)
def create_summary(req: VideoRequest) -> SummaryResponse:
    t = _load(req.url)
    summary = _guard_llm(llm.summarize, t.text, t.title)
    return SummaryResponse(**_meta(t), summary=summary)


@router.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest) -> AskResponse:
    t = _load(req.url)
    answer = _guard_llm(llm.answer_question, t.text, req.question, t.title)
    return AskResponse(**_meta(t), question=req.question, answer=answer)


@router.post("/mindmap", response_model=MindMapResponse)
def create_mind_map(req: VideoRequest) -> MindMapResponse:
    t = _load(req.url)
    mermaid = _guard_llm(llm.mind_map, t.text, t.title)
    return MindMapResponse(**_meta(t), mermaid=mermaid)
