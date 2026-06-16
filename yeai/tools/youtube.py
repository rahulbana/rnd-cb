"""Summarize a YouTube video given its URL.

Pulls the video's transcript (captions) and basic metadata (title/author),
then returns that text so the agent can summarize it. No API key is required:
metadata comes from YouTube's public oEmbed endpoint and the transcript from
the ``youtube-transcript-api`` package.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qs, urlparse

from .base import Tool
from .http import get_json

# How much transcript text to hand back to the model (characters).
_MAX_CHARS = 8000
_OEMBED = "https://www.youtube.com/oembed"


def extract_video_id(url: str) -> Optional[str]:
    """Pull the 11-character video id out of any common YouTube URL form."""
    url = url.strip()
    parsed = urlparse(url if "//" in url else "https://" + url)
    host = parsed.netloc.lower().replace("www.", "")
    path = parsed.path

    if host in ("youtu.be", "y2u.be"):
        candidate = path.lstrip("/").split("/")[0]
        return candidate or None

    if "youtube.com" in host or "youtube-nocookie.com" in host:
        if path == "/watch":
            values = parse_qs(parsed.query).get("v")
            return values[0] if values else None
        for prefix in ("/embed/", "/shorts/", "/v/", "/live/"):
            if path.startswith(prefix):
                return path[len(prefix):].split("/")[0] or None

    # Bare id passed directly.
    if len(url) == 11 and "/" not in url and "." not in url:
        return url
    return None


def _fetch_metadata(url: str) -> tuple[str, str]:
    """Best-effort (title, author) via the public oEmbed endpoint."""
    try:
        data = get_json(_OEMBED, params={"url": url, "format": "json"})
        return data.get("title", ""), data.get("author_name", "")
    except Exception:  # noqa: BLE001 - metadata is optional.
        return "", ""


def _fetch_transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi

    # Support both the 1.x instance API (fetch) and the older classmethod API.
    try:
        snippets = YouTubeTranscriptApi().fetch(video_id)
        parts = [getattr(s, "text", "") for s in snippets]
    except AttributeError:  # pragma: no cover - older library versions.
        raw = YouTubeTranscriptApi.get_transcript(video_id)  # type: ignore[attr-defined]
        parts = [seg.get("text", "") for seg in raw]

    return " ".join(p for p in parts if p).strip()


def _summarize_youtube(url: str) -> str:
    video_id = extract_video_id(url)
    if not video_id:
        return f"Could not parse a YouTube video id from {url!r}."

    title, author = _fetch_metadata(url)

    try:
        transcript = _fetch_transcript(video_id)
    except Exception as exc:  # noqa: BLE001 - surface a useful message.
        name = type(exc).__name__
        return (
            f"Could not fetch a transcript for video {video_id} ({name}: {exc}). "
            "The video may have captions disabled or be unavailable."
            + (f" Video title: {title}." if title else "")
        )

    if not transcript:
        return f"No transcript text was available for video {video_id}."

    truncated = len(transcript) > _MAX_CHARS
    if truncated:
        transcript = transcript[:_MAX_CHARS] + "..."

    meta = []
    if title:
        meta.append(f"Title: {title}")
    if author:
        meta.append(f"Channel: {author}")
    meta.append(f"Video URL: https://www.youtube.com/watch?v={video_id}")
    if truncated:
        meta.append("(transcript truncated)")

    return (
        "\n".join(meta)
        + "\n\nTranscript (summarize this for the user):\n\n"
        + transcript
    )


YOUTUBE_TOOL = Tool(
    name="summarize_youtube_video",
    description=(
        "Fetch the transcript and metadata of a YouTube video by its URL and "
        "return them so you can summarize the video for the user. Accepts "
        "youtube.com/watch, youtu.be, /shorts and /embed links."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full YouTube video URL.",
            }
        },
        "required": ["url"],
    },
    handler=_summarize_youtube,
)

TOOLS = [YOUTUBE_TOOL]
