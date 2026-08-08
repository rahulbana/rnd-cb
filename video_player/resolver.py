"""Resolve YouTube and other site URLs to a playable stream via yt-dlp.

Extraction can take a few seconds and hits the network, so it runs on a
``QThread`` worker and reports back with a signal. If yt-dlp is not installed
the resolver reports a clear error rather than crashing.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal


class ResolveWorker(QObject):
    """Runs a single yt-dlp extraction and emits the result."""

    resolved = Signal(str, str)   # (stream_url, title)
    failed = Signal(str)          # error message

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url

    def run(self) -> None:
        try:
            import yt_dlp  # noqa: WPS433 - imported lazily; optional dependency
        except ImportError:
            self.failed.emit(
                "yt-dlp is not installed. Run: pip install yt-dlp"
            )
            return

        # Prefer a single progressive stream libvlc can play directly; fall
        # back to best available. yt-dlp will hand us an HLS/DASH manifest URL
        # for adaptive-only sources, which libvlc handles too.
        options = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "format": "best[ext=mp4]/best",
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(self._url, download=False)
        except Exception as exc:  # noqa: BLE001 - surface any yt-dlp failure
            self.failed.emit(f"Could not resolve URL: {exc}")
            return

        if info is None:
            self.failed.emit("Could not resolve URL: no media found.")
            return

        # A playlist page returns entries; take the first playable one.
        if "entries" in info and info["entries"]:
            info = next((e for e in info["entries"] if e), info)

        stream_url = self._pick_url(info)
        if not stream_url:
            self.failed.emit("Could not find a playable stream for this URL.")
            return

        title = info.get("title") or self._url
        self.resolved.emit(stream_url, title)

    @staticmethod
    def _pick_url(info: dict) -> Optional[str]:
        """Choose the best usable URL from an extracted info dict."""
        if info.get("url"):
            return info["url"]
        formats = info.get("formats") or []
        # Prefer a format that carries both audio and video.
        for fmt in reversed(formats):
            if fmt.get("url") and fmt.get("acodec") != "none" and fmt.get("vcodec") != "none":
                return fmt["url"]
        for fmt in reversed(formats):
            if fmt.get("url"):
                return fmt["url"]
        return None


class UrlResolver(QObject):
    """Owns worker threads and forwards their results to the UI."""

    resolved = Signal(str, str)   # (stream_url, title)
    failed = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._thread: Optional[QThread] = None
        self._worker: Optional[ResolveWorker] = None

    def resolve(self, url: str) -> None:
        # Only one resolution at a time keeps ownership simple.
        self._cleanup()
        self._thread = QThread(self)
        self._worker = ResolveWorker(url)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.resolved.connect(self._on_resolved)
        self._worker.failed.connect(self._on_failed)
        self._thread.start()

    def _on_resolved(self, stream_url: str, title: str) -> None:
        self.resolved.emit(stream_url, title)
        self._cleanup()

    def _on_failed(self, message: str) -> None:
        self.failed.emit(message)
        self._cleanup()

    def _cleanup(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
        self._worker = None
