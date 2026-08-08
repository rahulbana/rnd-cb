"""The black surface libvlc renders video into.

It owns the native window handle passed to VLC and forwards mouse gestures
(single click to toggle play, double click to toggle fullscreen) to the main
window.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QFrame


class VideoFrame(QFrame):
    """A solid black frame used as the VLC video output target."""

    clicked = Signal()
    double_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # Paint the widget's own background black so there is no flash of the
        # window colour before/after video is showing.
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.setPalette(palette)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def video_handle(self) -> int:
        """Native window id to hand to ``PlayerEngine.set_output_window``."""
        return int(self.winId())

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
