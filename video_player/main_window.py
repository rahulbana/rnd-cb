"""The main application window.

Owns the video surface, control bar, playlist dock, menus and keyboard
shortcuts, and wires them to a :class:`PlayerEngine` and :class:`UrlResolver`.
"""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QCursor, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from . import __app_name__, __version__
from .controls import ControlBar
from .player import PlayerEngine
from .playlist import Playlist, PlaylistItem, PlaylistWidget
from .resolver import UrlResolver
from .utils import (
    SUBTITLE_EXTENSIONS,
    display_name,
    is_media_file,
    is_url,
    is_youtube_or_site_url,
)
from .video_frame import VideoFrame

SEEK_STEP_MS = 5000        # arrow-key seek
SEEK_STEP_LARGE_MS = 60000  # page/ctrl seek
VOLUME_STEP = 5


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(__app_name__)
        self.resize(960, 600)
        self.setAcceptDrops(True)

        self.engine = PlayerEngine(self)
        self.playlist = Playlist()
        self.resolver = UrlResolver(self)

        # Fullscreen auto-hide: poll the global cursor and hide the chrome and
        # cursor after a few seconds of no movement while playing fullscreen.
        self._last_cursor_pos = QCursor.pos()
        self._idle_ms = 0
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(500)
        self._idle_timer.timeout.connect(self._check_cursor_idle)

        self._build_ui()
        self._build_menus()
        self._build_shortcuts()
        self._connect_signals()

        # Bind VLC output to the video frame once it has a native handle.
        QTimer.singleShot(0, self._bind_video_output)
        self.engine.set_volume(self.controls.volume_slider.value())

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.video_frame = VideoFrame()
        self.video_frame.setMinimumHeight(200)
        layout.addWidget(self.video_frame, stretch=1)

        self.controls = ControlBar()
        layout.addWidget(self.controls, stretch=0)

        self.setCentralWidget(central)

        # Playlist dock on the right.
        self.playlist_view = PlaylistWidget()
        dock = QDockWidget("Playlist", self)
        dock.setObjectName("playlist_dock")
        dock.setWidget(self.playlist_view)
        dock.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable
        )
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.playlist_dock = dock

        self.status = self.statusBar()
        self.status_label = QLabel("Ready")
        self.status.addWidget(self.status_label)

    def _build_menus(self) -> None:
        menubar = self.menuBar()

        # --- Media ----------------------------------------------------------
        media_menu = menubar.addMenu("&Media")
        self._add_action(media_menu, "Open File(s)…", self.open_files, "Ctrl+O")
        self._add_action(media_menu, "Open Folder…", self.open_folder, "Ctrl+F")
        self._add_action(media_menu, "Open URL / YouTube…", self.open_url, "Ctrl+U")
        media_menu.addSeparator()
        self._add_action(media_menu, "Quit", self.close, "Ctrl+Q")

        # --- Playback -------------------------------------------------------
        playback_menu = menubar.addMenu("&Playback")
        self._add_action(playback_menu, "Play/Pause", self.toggle_play, "Space")
        self._add_action(playback_menu, "Stop", self.stop, "S")
        self._add_action(playback_menu, "Previous", self.play_previous, "P")
        self._add_action(playback_menu, "Next", self.play_next, "N")
        playback_menu.addSeparator()
        self._add_action(playback_menu, "Jump +5s", lambda: self.engine.seek_relative(SEEK_STEP_MS), "Right")
        self._add_action(playback_menu, "Jump -5s", lambda: self.engine.seek_relative(-SEEK_STEP_MS), "Left")

        # --- Audio ----------------------------------------------------------
        self.audio_menu = menubar.addMenu("&Audio")
        self.audio_track_menu = self.audio_menu.addMenu("Audio Track")
        self.audio_menu.addSeparator()
        self._add_action(self.audio_menu, "Increase Volume", lambda: self.nudge_volume(VOLUME_STEP), "Up")
        self._add_action(self.audio_menu, "Decrease Volume", lambda: self.nudge_volume(-VOLUME_STEP), "Down")
        self._add_action(self.audio_menu, "Mute", self.toggle_mute, "M")
        self.audio_menu.aboutToShow.connect(self._populate_audio_tracks)

        # --- Subtitle -------------------------------------------------------
        self.subtitle_menu = menubar.addMenu("Subti&tle")
        self.subtitle_track_menu = self.subtitle_menu.addMenu("Subtitle Track")
        self.subtitle_menu.addSeparator()
        self._add_action(self.subtitle_menu, "Add Subtitle File…", self.add_subtitle_file)
        self.subtitle_menu.aboutToShow.connect(self._populate_subtitle_tracks)

        # --- View -----------------------------------------------------------
        view_menu = menubar.addMenu("&View")
        self._add_action(view_menu, "Fullscreen", self.toggle_fullscreen, "F")
        self.toggle_playlist_action = self._add_action(
            view_menu, "Toggle Playlist", self.toggle_playlist, "Ctrl+L"
        )

        # --- Help -----------------------------------------------------------
        help_menu = menubar.addMenu("&Help")
        self._add_action(help_menu, "About", self.show_about)

    def _build_shortcuts(self) -> None:
        # Fullscreen exit shortcut (Esc) needs a window-level action.
        esc = QAction(self)
        esc.setShortcut(QKeySequence(Qt.Key_Escape))
        esc.triggered.connect(self._exit_fullscreen)
        self.addAction(esc)

    def _connect_signals(self) -> None:
        c = self.controls
        c.play_pause_clicked.connect(self.toggle_play)
        c.stop_clicked.connect(self.stop)
        c.next_clicked.connect(self.play_next)
        c.previous_clicked.connect(self.play_previous)
        c.seek_requested.connect(self.engine.set_position)
        c.volume_changed.connect(self.set_volume)
        c.mute_toggled.connect(self.toggle_mute)
        c.speed_changed.connect(self.set_speed)
        c.fullscreen_clicked.connect(self.toggle_fullscreen)

        self.engine.position_changed.connect(c.update_position)
        self.engine.playing_changed.connect(c.set_playing)
        self.engine.playing_changed.connect(self._on_playing_changed)
        self.engine.end_reached.connect(self._on_end_reached)
        self.engine.error_occurred.connect(self._on_engine_error)

        self.playlist_view.play_requested.connect(self.play_index)
        self.playlist_view.remove_requested.connect(self.remove_index)

        self.video_frame.clicked.connect(self.toggle_play)
        self.video_frame.double_clicked.connect(self.toggle_fullscreen)

        self.resolver.resolved.connect(self._on_url_resolved)
        self.resolver.failed.connect(self._on_url_failed)

    # -------------------------------------------------------------- utilities
    def _add_action(self, menu: QMenu, text: str, slot, shortcut: str = "") -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _bind_video_output(self) -> None:
        self.engine.set_output_window(self.video_frame.video_handle())

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    # ----------------------------------------------------------- opening media
    def open_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Media", "", "Media Files (*.*)"
        )
        if not paths:
            return
        first = len(self.playlist) == 0
        for path in paths:
            self._enqueue(path)
        if first:
            self.play_index(0)
        self._refresh_playlist()

    def open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if not folder:
            return
        first = len(self.playlist) == 0
        added = 0
        for name in sorted(os.listdir(folder)):
            full = os.path.join(folder, name)
            if os.path.isfile(full) and is_media_file(full):
                self._enqueue(full)
                added += 1
        if added and first:
            self.play_index(0)
        self._refresh_playlist()
        self._set_status(f"Added {added} file(s) from folder.")

    def open_url(self) -> None:
        url, ok = QInputDialog.getText(
            self, "Open URL", "Enter a video URL (YouTube, stream, etc.):"
        )
        url = url.strip()
        if not ok or not url:
            return
        self._enqueue(url)
        # Play it immediately.
        self.play_index(len(self.playlist) - 1)
        self._refresh_playlist()

    def _enqueue(self, source: str) -> PlaylistItem:
        """Add a path/URL to the playlist without starting playback."""
        needs_resolve = is_youtube_or_site_url(source)
        item = PlaylistItem(
            mrl=source,
            title=display_name(source),
            source=source,
            needs_resolve=needs_resolve,
        )
        self.playlist.add(item)
        return item

    # --------------------------------------------------------------- playback
    def play_index(self, index: int) -> None:
        item = self.playlist.set_index(index)
        if item is None:
            return
        self._refresh_playlist()
        if item.needs_resolve and is_url(item.source):
            self._set_status(f"Resolving {item.source} …")
            self.setWindowTitle(f"Resolving… — {__app_name__}")
            self.resolver.resolve(item.source)
            return
        self._play_item(item)

    def _play_item(self, item: PlaylistItem) -> None:
        self.engine.open(item.mrl, play=True)
        self.video_frame.set_placeholder_visible(False)
        self.setWindowTitle(f"{item.title} — {__app_name__}")
        self._set_status(f"Playing: {item.title}")

    def toggle_play(self) -> None:
        if self.playlist.current() is None:
            self.open_files()
            return
        self.engine.toggle_pause()

    def stop(self) -> None:
        self.engine.stop()
        self.video_frame.set_placeholder_visible(True)
        self._set_status("Stopped")

    def play_next(self) -> None:
        item = self.playlist.next()
        if item is None:
            self._set_status("End of playlist.")
            return
        self.play_index(self.playlist.index)

    def play_previous(self) -> None:
        item = self.playlist.previous()
        if item is None:
            return
        self.play_index(self.playlist.index)

    def remove_index(self, index: int) -> None:
        was_current = index == self.playlist.index
        self.playlist.remove(index)
        if was_current:
            self.engine.stop()
        self._refresh_playlist()

    def _refresh_playlist(self) -> None:
        self.playlist_view.rebuild(self.playlist)

    # ------------------------------------------------------------------ audio
    def set_volume(self, volume: int) -> None:
        self.engine.set_volume(volume)
        if volume > 0 and self.engine.is_muted():
            self.engine.set_muted(False)
        self.controls.set_muted(self.engine.is_muted())

    def nudge_volume(self, delta: int) -> None:
        new_volume = max(0, min(100, self.controls.volume_slider.value() + delta))
        self.controls.set_volume_display(new_volume)
        self.set_volume(new_volume)

    def toggle_mute(self) -> None:
        self.engine.set_muted(not self.engine.is_muted())
        self.controls.set_muted(self.engine.is_muted())

    def set_speed(self, rate: float) -> None:
        self.engine.set_rate(rate)
        self.controls.set_speed_display(rate)
        self._set_status(f"Speed: {rate:g}x")

    # ----------------------------------------------------------------- tracks
    def _populate_audio_tracks(self) -> None:
        self._populate_track_menu(
            self.audio_track_menu,
            self.engine.audio_tracks(),
            self.engine.current_audio_track(),
            self.engine.set_audio_track,
        )

    def _populate_subtitle_tracks(self) -> None:
        self._populate_track_menu(
            self.subtitle_track_menu,
            self.engine.subtitle_tracks(),
            self.engine.current_subtitle_track(),
            self.engine.set_subtitle_track,
        )

    def _populate_track_menu(self, menu: QMenu, tracks, current: int, setter) -> None:
        menu.clear()
        group = QActionGroup(menu)
        group.setExclusive(True)
        if not tracks:
            placeholder = menu.addAction("(none available)")
            placeholder.setEnabled(False)
            return
        for track_id, label in tracks:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(track_id == current)
            action.triggered.connect(lambda _checked, tid=track_id: setter(tid))
            group.addAction(action)

    def add_subtitle_file(self) -> None:
        exts = " ".join(f"*{e}" for e in sorted(SUBTITLE_EXTENSIONS))
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Subtitle File", "", f"Subtitles ({exts})"
        )
        if not path:
            return
        if self.engine.add_subtitle_file(path):
            self._set_status(f"Loaded subtitle: {os.path.basename(path)}")
        else:
            QMessageBox.warning(self, __app_name__, "Failed to load the subtitle file.")

    # -------------------------------------------------------------- fullscreen
    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self) -> None:
        self.menuBar().hide()
        self.status.hide()
        self.playlist_dock.hide()
        self.controls.set_fullscreen_display(True)
        self.showFullScreen()
        # Begin watching for an idle cursor so the chrome can fade away.
        self._idle_ms = 0
        self._last_cursor_pos = QCursor.pos()
        self._idle_timer.start()

    def _exit_fullscreen(self) -> None:
        if not self.isFullScreen():
            return
        self._idle_timer.stop()
        self._reveal_chrome()
        self.menuBar().show()
        self.status.show()
        self.playlist_dock.show()
        self.controls.set_fullscreen_display(False)
        self.showNormal()

    def _check_cursor_idle(self) -> None:
        """Hide controls and cursor after a few idle seconds in fullscreen."""
        if not self.isFullScreen():
            return
        pos = QCursor.pos()
        if pos != self._last_cursor_pos:
            self._last_cursor_pos = pos
            self._idle_ms = 0
            self._reveal_chrome()
            return
        self._idle_ms += self._idle_timer.interval()
        if self._idle_ms >= 2500 and self.engine.is_playing():
            self._hide_chrome()

    def _hide_chrome(self) -> None:
        self.controls.hide()
        self.setCursor(Qt.BlankCursor)

    def _reveal_chrome(self) -> None:
        self.controls.show()
        self.unsetCursor()

    def toggle_playlist(self) -> None:
        self.playlist_dock.setVisible(not self.playlist_dock.isVisible())

    # --------------------------------------------------------- engine reactions
    def _on_playing_changed(self, playing: bool) -> None:
        if playing:
            item = self.playlist.current()
            if item:
                self.setWindowTitle(f"{item.title} — {__app_name__}")

    def _on_end_reached(self) -> None:
        # VLC forbids calling back into the player from its event thread, so
        # defer advancing to the next track onto the GUI event loop.
        QTimer.singleShot(0, self.play_next)

    def _on_engine_error(self, message: str) -> None:
        self._set_status(message)
        QTimer.singleShot(0, self.play_next)

    def _on_url_resolved(self, stream_url: str, title: str) -> None:
        item = self.playlist.current()
        if item is None:
            return
        item.mrl = stream_url
        item.title = title
        item.needs_resolve = False  # keep the resolved URL for replays this session
        self._refresh_playlist()
        self._play_item(item)

    def _on_url_failed(self, message: str) -> None:
        self._set_status(message)
        QMessageBox.warning(self, __app_name__, message)

    # ---------------------------------------------------------- drag and drop
    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt override
        mime = event.mimeData()
        sources = []
        if mime.hasUrls():
            for url in mime.urls():
                sources.append(url.toLocalFile() if url.isLocalFile() else url.toString())
        elif mime.hasText():
            sources.append(mime.text().strip())
        if not sources:
            return
        first = len(self.playlist) == 0
        for source in sources:
            if source:
                self._enqueue(source)
        self._refresh_playlist()
        if first:
            self.play_index(0)

    # ------------------------------------------------------------------- misc
    def show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {__app_name__}",
            f"<h3>{__app_name__} {__version__}</h3>"
            "<p>A VLC-powered desktop media player.</p>"
            "<p>Plays local files and online/streaming URLs (YouTube via "
            "yt-dlp). Built with PySide6 and libvlc.</p>",
        )

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.engine.release()
        super().closeEvent(event)
