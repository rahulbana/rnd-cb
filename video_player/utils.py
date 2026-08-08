"""Small helpers shared across the app."""

from __future__ import annotations

import os
from urllib.parse import urlparse

# Extensions we treat as directly playable local media.
MEDIA_EXTENSIONS = {
    # video
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".3gp", ".ts", ".m2ts", ".vob", ".ogv", ".mxf",
    # audio
    ".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".oga", ".opus",
    ".wma", ".ac3", ".aiff", ".alac", ".ape", ".mid", ".midi",
}

SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".sub", ".vtt", ".idx"}


def format_time(ms: int) -> str:
    """Format a duration in milliseconds as H:MM:SS or M:SS."""
    if ms is None or ms < 0:
        return "--:--"
    total_seconds = int(ms // 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def is_url(path: str) -> bool:
    """Return True if the string looks like a network URL rather than a path."""
    try:
        parsed = urlparse(path)
    except (ValueError, AttributeError):
        return False
    return parsed.scheme in {"http", "https", "rtsp", "rtmp", "mms", "udp", "ftp"}


def is_media_file(path: str) -> bool:
    """Return True if the path points to a file with a known media extension."""
    return os.path.splitext(path)[1].lower() in MEDIA_EXTENSIONS


def is_youtube_or_site_url(url: str) -> bool:
    """Heuristic: a network URL that is not a direct media/stream file.

    These are the URLs we hand to yt-dlp for resolution. Direct links to
    ``.mp4``/``.m3u8``/etc. are passed straight to libvlc instead.
    """
    if not is_url(url):
        return False
    lowered = url.lower()
    # Direct media or streaming manifest -> let VLC handle it natively.
    if any(lowered.split("?")[0].endswith(ext) for ext in MEDIA_EXTENSIONS):
        return False
    if any(token in lowered for token in (".m3u8", ".mpd", ".ism")):
        return False
    return True


def display_name(path: str) -> str:
    """A human-friendly label for a media path or URL."""
    if is_url(path):
        return path
    return os.path.basename(path) or path
