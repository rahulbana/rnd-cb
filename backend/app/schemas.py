from pydantic import BaseModel, Field


class VideoRequest(BaseModel):
    url: str = Field(..., description="A YouTube video URL or bare video id.")


class AskRequest(VideoRequest):
    question: str = Field(..., min_length=1, description="Question about the video.")


class VideoMeta(BaseModel):
    video_id: str
    title: str | None = None
    author: str | None = None
    thumbnail_url: str | None = None


class TranscriptResponse(VideoMeta):
    transcript: str
    language: str | None = None
    char_count: int


class SummaryResponse(VideoMeta):
    summary: str


class AskResponse(VideoMeta):
    question: str
    answer: str


class MindMapResponse(VideoMeta):
    mermaid: str
