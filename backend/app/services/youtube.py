"""Fetch YouTube video metadata and transcripts.

Transcripts come from YouTube's own caption tracks via ``youtube-transcript-api``
(no audio download required). Basic metadata (title / author / thumbnail) is
pulled from the public oEmbed endpoint. Transcripts are cached in memory per
video id so repeated summary / Q&A / mind-map calls don't re-fetch.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    AgeRestricted,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
)

logger = logging.getLogger("yt_research.youtube")


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
    """Return (joined_text, language_code) for a video's captions.

    Uses the youtube-transcript-api 1.x instance API.
    """
    api = YouTubeTranscriptApi()
    try:
        transcript_list = api.list(video_id)
        # Prefer a manually created English track, then any English track,
        # then fall back to the first available track (often auto-generated).
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
            for t in transcript_list:
                transcript = t
                break
        if transcript is None:
            raise TranscriptError("No transcript tracks available for this video.")

        fetched = transcript.fetch()
        language = getattr(transcript, "language_code", None)
    except (TranscriptsDisabled, NoTranscriptFound):
        raise TranscriptError(
            "This video has no captions available, so it can't be analyzed."
        )
    except InvalidVideoId:
        raise TranscriptError("That doesn't look like a valid YouTube video.")
    except (VideoUnavailable, VideoUnplayable, AgeRestricted):
        raise TranscriptError(
            "This video is unavailable, private, or age-restricted, so its "
            "transcript can't be retrieved."
        )
    except (RequestBlocked, IpBlocked):
        raise TranscriptError(
            "YouTube is currently blocking transcript requests from this network "
            "/ IP. Try again later, or run the backend from a different network."
        )
    except TranscriptError:
        raise
    except Exception as exc:  # network / parsing / library errors
        # Surface the real cause in the server console for debugging.
        logger.exception("Transcript fetch failed for video_id=%s", video_id)
        raise TranscriptError(
            f"Failed to fetch transcript ({type(exc).__name__}): {exc}"
        ) from exc

    # FetchedTranscript is iterable of snippets; to_raw_data() -> list of dicts.
    try:
        raw = fetched.to_raw_data()
        parts = [(item.get("text") or "").strip() for item in raw]
    except AttributeError:
        parts = [(getattr(s, "text", "") or "").strip() for s in fetched]

    text = re.sub(r"\s+", " ", " ".join(parts)).strip()
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
