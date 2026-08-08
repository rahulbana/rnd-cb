"""Playback engine: a thin, Qt-friendly wrapper around libvlc (python-vlc).

The wrapper owns a single ``MediaPlayer`` instance and exposes the operations
the UI needs (open/play/pause/seek/volume/tracks/speed) plus a set of Qt
signals so the UI can react to state and position changes without polling VLC
internals directly.
"""

from __future__ import annotations

import sys
from typing import List, Optional, Tuple

import vlc
from PySide6.QtCore import QObject, QTimer, Signal


class PlayerEngine(QObject):
    """Wraps a libvlc media player and emits Qt signals for UI updates."""

    # position in the media, in milliseconds, and total length in milliseconds
    position_changed = Signal(int, int)
    # True when playing, False when paused/stopped
    playing_changed = Signal(bool)
    # emitted when the current media reaches its end
    end_reached = Signal()
    # emitted when VLC reports a hard playback error
    error_occurred = Signal(str)
    # emitted once media is parsed and length/tracks are known
    media_ready = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        # --no-xlib avoided; we let VLC pick sane defaults. Quiet the logs.
        self._instance = vlc.Instance("--quiet", "--no-video-title-show")
        if self._instance is None:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "Failed to create a libvlc instance. Is VLC installed?"
            )
        self._player = self._instance.media_player_new()
        self._length_ms = 0
        self._current_media: Optional[vlc.Media] = None

        # VLC callbacks arrive on VLC's own threads, so we never touch Qt
        # widgets from them; we only emit signals (queued to the GUI thread).
        events = self._player.event_manager()
        events.event_attach(
            vlc.EventType.MediaPlayerEndReached, self._on_end_reached
        )
        events.event_attach(
            vlc.EventType.MediaPlayerEncounteredError, self._on_error
        )
        events.event_attach(
            vlc.EventType.MediaPlayerPlaying,
            lambda _e: self.playing_changed.emit(True),
        )
        events.event_attach(
            vlc.EventType.MediaPlayerPaused,
            lambda _e: self.playing_changed.emit(False),
        )
        events.event_attach(
            vlc.EventType.MediaPlayerStopped,
            lambda _e: self.playing_changed.emit(False),
        )

        # Poll position on the GUI thread; simplest reliable way to drive the
        # seek slider and time labels.
        self._poll = QTimer(self)
        self._poll.setInterval(200)
        self._poll.timeout.connect(self._emit_position)
        self._poll.start()

    # ------------------------------------------------------------------ setup
    def set_output_window(self, win_id: int) -> None:
        """Bind video output to a native window handle for the current OS."""
        if sys.platform.startswith("linux"):
            self._player.set_xwindow(int(win_id))
        elif sys.platform == "win32":
            self._player.set_hwnd(int(win_id))
        elif sys.platform == "darwin":
            self._player.set_nsobject(int(win_id))

    # ------------------------------------------------------------------ media
    def open(self, mrl: str, *, play: bool = True) -> None:
        """Load a media resource locator (local path or network URL)."""
        media = self._instance.media_new(mrl)
        # Parse asynchronously so length/tracks become available.
        try:
            media.parse_with_options(vlc.MediaParseFlag.network, 5000)
        except Exception:  # noqa: BLE001 - older bindings lack this API
            pass
        self._current_media = media
        self._player.set_media(media)
        self._length_ms = 0
        if play:
            self.play()
        self.media_ready.emit()

    # --------------------------------------------------------------- controls
    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        """Pause without toggling; no-op if already paused."""
        if self._player.is_playing():
            self._player.pause()

    def toggle_pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()
        self.playing_changed.emit(False)
        self.position_changed.emit(0, self._length_ms)

    def is_playing(self) -> bool:
        return bool(self._player.is_playing())

    def set_position(self, ms: int) -> None:
        """Seek to an absolute time in milliseconds."""
        self._player.set_time(int(ms))

    def seek_relative(self, delta_ms: int) -> None:
        current = self._player.get_time()
        if current is None or current < 0:
            return
        target = max(0, current + delta_ms)
        self._player.set_time(int(target))

    # ------------------------------------------------------------------ audio
    def set_volume(self, volume: int) -> None:
        self._player.audio_set_volume(max(0, min(200, int(volume))))

    def get_volume(self) -> int:
        return int(self._player.audio_get_volume())

    def set_muted(self, muted: bool) -> None:
        self._player.audio_set_mute(bool(muted))

    def is_muted(self) -> bool:
        return bool(self._player.audio_get_mute())

    # ------------------------------------------------------------------ speed
    def set_rate(self, rate: float) -> None:
        self._player.set_rate(float(rate))

    def get_rate(self) -> float:
        return float(self._player.get_rate())

    # ----------------------------------------------------------------- tracks
    def audio_tracks(self) -> List[Tuple[int, str]]:
        return self._describe(self._player.audio_get_track_description())

    def current_audio_track(self) -> int:
        return int(self._player.audio_get_track())

    def set_audio_track(self, track_id: int) -> None:
        self._player.audio_set_track(int(track_id))

    def subtitle_tracks(self) -> List[Tuple[int, str]]:
        return self._describe(self._player.video_get_spu_description())

    def current_subtitle_track(self) -> int:
        return int(self._player.video_get_spu())

    def set_subtitle_track(self, track_id: int) -> None:
        self._player.video_set_spu(int(track_id))

    def add_subtitle_file(self, path: str) -> bool:
        """Load an external subtitle file and enable it."""
        try:
            return bool(self._player.add_slave(vlc.MediaSlaveType.subtitle, path, True))
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    def _describe(descriptions) -> List[Tuple[int, str]]:
        """Normalise VLC track descriptions to (id, label) tuples."""
        result: List[Tuple[int, str]] = []
        for track_id, name in descriptions or []:
            label = name.decode("utf-8", "replace") if isinstance(name, bytes) else str(name)
            result.append((int(track_id), label))
        return result

    # --------------------------------------------------------------- teardown
    def release(self) -> None:
        self._poll.stop()
        try:
            self._player.stop()
        except Exception:  # noqa: BLE001
            pass
        self._player.release()
        self._instance.release()

    # ---------------------------------------------------------------- private
    def _emit_position(self) -> None:
        if self._length_ms <= 0:
            length = self._player.get_length()
            if length and length > 0:
                self._length_ms = int(length)
        current = self._player.get_time()
        if current is None or current < 0:
            current = 0
        self.position_changed.emit(int(current), int(self._length_ms))

    def _on_end_reached(self, _event) -> None:
        self.end_reached.emit()

    def _on_error(self, _event) -> None:
        self.error_occurred.emit("VLC could not play this media.")
