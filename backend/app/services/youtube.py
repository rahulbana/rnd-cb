"""Fetch YouTube video metadata and transcripts.

Transcripts come from YouTube's own caption tracks via ``youtube-transcript-api``
(no audio download required). Basic metadata (title / author / thumbnail) is
pulled from the public oEmbed endpoint. Transcripts are cached in memory per
video id so repeated summary / Q&A / mind-map calls don't re-fetch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)


class TranscriptError(Exception):
    """Raised when a transcript cannot be retrieved for a video."""


class InvalidURLError(Exception):
    """Raised when a YouTube URL / id cannot be parsed."""


@dataclass
class Transcript:
    video_id: str
    text: str
    language: str | None
    title: str | None = None
    author: str | None = None
    thumbnail_url: str | None = None


_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Simple process-local cache: video_id -> Transcript
_CACHE: dict[str, Transcript] = {}


def extract_video_id(url_or_id: str) -> str:
    """Extract an 11-character YouTube video id from a URL or bare id."""
    value = (url_or_id or "").strip()
    if not value:
        raise InvalidURLError("No URL or video id provided.")

    # Already a bare id
    if _VIDEO_ID_RE.match(value):
        return value

    parsed = urlparse(value if "//" in value else f"https://{value}")
    host = (parsed.hostname or "").lower().replace("www.", "")

    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
        if _VIDEO_ID_RE.match(candidate):
            return candidate

    if host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        # /watch?v=ID
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id and _VIDEO_ID_RE.match(query_id):
            return query_id
        # /embed/ID, /shorts/ID, /live/ID, /v/ID
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live", "v"}:
            if _VIDEO_ID_RE.match(parts[1]):
                return parts[1]

    raise InvalidURLError(f"Could not extract a YouTube video id from: {url_or_id!r}")


def _fetch_metadata(video_id: str) -> dict:
    """Best-effort title / author / thumbnail via oEmbed. Never raises."""
    try:
        resp = httpx.get(
            "https://www.youtube.com/oembed",
            params={
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "format": "json",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "title": data.get("title"),
            "author": data.get("author_name"),
            "thumbnail_url": data.get("thumbnail_url"),
        }
    except Exception:
        return {
            "title": None,
            "author": None,
            "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        }


def _fetch_transcript_text(video_id: str) -> tuple[str, str | None]:
    """Return (joined_text, language_code) for a video's captions."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # Prefer a manually created English track, then any English, then
        # any generated track, then anything translatable to English.
        transcript = None
        try:
            transcript = transcript_list.find_manually_created_transcript(
                ["en", "en-US", "en-GB"]
            )
        except Exception:
            pass
        if transcript is None:
            try:
                transcript = transcript_list.find_transcript(["en", "en-US", "en-GB"])
            except Exception:
                pass
        if transcript is None:
            # Fall back to the first available transcript.
            for t in transcript_list:
                transcript = t
                break
        if transcript is None:
            raise TranscriptError("No transcript tracks available for this video.")

        entries = transcript.fetch()
        language = getattr(transcript, "language_code", None)
    except (TranscriptsDisabled, NoTranscriptFound):
        raise TranscriptError(
            "This video has no captions available, so it can't be analyzed."
        )
    except VideoUnavailable:
        raise TranscriptError("This video is unavailable.")
    except TranscriptError:
        raise
    except Exception as exc:  # network / parsing / library errors
        raise TranscriptError(f"Failed to fetch transcript: {exc}") from exc

    text = " ".join(
        (getattr(e, "text", None) or (e.get("text") if isinstance(e, dict) else "") or "").strip()
        for e in entries
    )
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise TranscriptError("The transcript for this video was empty.")
    return text, language


def get_transcript(url_or_id: str, *, use_cache: bool = True) -> Transcript:
    """Resolve a URL/id to a cached ``Transcript`` (metadata + caption text)."""
    video_id = extract_video_id(url_or_id)

    if use_cache and video_id in _CACHE:
        return _CACHE[video_id]

    text, language = _fetch_transcript_text(video_id)
    meta = _fetch_metadata(video_id)

    transcript = Transcript(
        video_id=video_id,
        text=text,
        language=language,
        title=meta.get("title"),
        author=meta.get("author"),
        thumbnail_url=meta.get("thumbnail_url"),
    )
    _CACHE[video_id] = transcript
    return transcript
