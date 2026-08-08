"""The transport control bar: seek slider, play/prev/next/stop, volume, speed.

The bar is intentionally passive: it emits signals for user intent and exposes
setters the main window calls to keep it in sync with the engine. It holds no
playback logic of its own.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .utils import format_time

# Playback rates offered in the speed selector.
SPEED_OPTIONS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]


class SeekSlider(QSlider):
    """A horizontal slider that seeks on click-anywhere, not just on the handle."""

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Horizontal, parent)
        self.setRange(0, 1000)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton and self.maximum() > self.minimum():
            ratio = event.position().x() / max(1, self.width())
            value = self.minimum() + round(ratio * (self.maximum() - self.minimum()))
            self.setValue(int(value))
            self.sliderMoved.emit(int(value))
        super().mousePressEvent(event)


class ControlBar(QWidget):
    """Bottom transport controls."""

    play_pause_clicked = Signal()
    stop_clicked = Signal()
    next_clicked = Signal()
    previous_clicked = Signal()
    seek_requested = Signal(int)          # target position in milliseconds
    volume_changed = Signal(int)          # 0..100
    mute_toggled = Signal()
    speed_changed = Signal(float)
    fullscreen_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._length_ms = 0
        self._seeking = False
        self._build_ui()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        style = self.style()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 8)
        outer.setSpacing(4)

        # --- seek row: elapsed / slider / total -----------------------------
        seek_row = QHBoxLayout()
        self.time_label = QLabel("0:00")
        self.time_label.setMinimumWidth(48)
        self.time_label.setAlignment(Qt.AlignCenter)

        self.seek_slider = SeekSlider()
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.sliderMoved.connect(self._on_seek_moved)

        self.duration_label = QLabel("0:00")
        self.duration_label.setMinimumWidth(48)
        self.duration_label.setAlignment(Qt.AlignCenter)

        seek_row.addWidget(self.time_label)
        seek_row.addWidget(self.seek_slider)
        seek_row.addWidget(self.duration_label)
        outer.addLayout(seek_row)

        # --- button row -----------------------------------------------------
        buttons = QHBoxLayout()
        buttons.setSpacing(6)

        self.play_button = self._tool_button(
            style.standardIcon(QStyle.SP_MediaPlay), "Play/Pause (Space)"
        )
        self.play_button.clicked.connect(self.play_pause_clicked)

        self.stop_button = self._tool_button(
            style.standardIcon(QStyle.SP_MediaStop), "Stop"
        )
        self.stop_button.clicked.connect(self.stop_clicked)

        self.prev_button = self._tool_button(
            style.standardIcon(QStyle.SP_MediaSkipBackward), "Previous (P)"
        )
        self.prev_button.clicked.connect(self.previous_clicked)

        self.next_button = self._tool_button(
            style.standardIcon(QStyle.SP_MediaSkipForward), "Next (N)"
        )
        self.next_button.clicked.connect(self.next_clicked)

        buttons.addWidget(self.prev_button)
        buttons.addWidget(self.play_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.next_button)

        buttons.addStretch(1)

        # speed selector
        buttons.addWidget(QLabel("Speed"))
        self.speed_combo = QComboBox()
        for rate in SPEED_OPTIONS:
            self.speed_combo.addItem(f"{rate:g}x", rate)
        self.speed_combo.setCurrentIndex(SPEED_OPTIONS.index(1.0))
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        buttons.addWidget(self.speed_combo)

        buttons.addSpacing(12)

        # mute + volume
        self.mute_button = self._tool_button(
            style.standardIcon(QStyle.SP_MediaVolume), "Mute (M)"
        )
        self.mute_button.clicked.connect(self.mute_toggled)
        buttons.addWidget(self.mute_button)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(110)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.valueChanged.connect(self.volume_changed)
        buttons.addWidget(self.volume_slider)

        buttons.addSpacing(12)

        self.fullscreen_button = self._tool_button(
            style.standardIcon(QStyle.SP_TitleBarMaxButton), "Fullscreen (F)"
        )
        self.fullscreen_button.clicked.connect(self.fullscreen_clicked)
        buttons.addWidget(self.fullscreen_button)

        outer.addLayout(buttons)

    def _tool_button(self, icon, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setIcon(icon)
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        return button

    # ------------------------------------------------------- state from engine
    def set_playing(self, playing: bool) -> None:
        style = self.style()
        icon = QStyle.SP_MediaPause if playing else QStyle.SP_MediaPlay
        self.play_button.setIcon(style.standardIcon(icon))

    def set_muted(self, muted: bool) -> None:
        style = self.style()
        icon = QStyle.SP_MediaVolumeMuted if muted else QStyle.SP_MediaVolume
        self.mute_button.setIcon(style.standardIcon(icon))

    def set_volume_display(self, volume: int) -> None:
        blocked = self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(int(volume))
        self.volume_slider.blockSignals(blocked)

    def set_speed_display(self, rate: float) -> None:
        if rate in SPEED_OPTIONS:
            blocked = self.speed_combo.blockSignals(True)
            self.speed_combo.setCurrentIndex(SPEED_OPTIONS.index(rate))
            self.speed_combo.blockSignals(blocked)

    def update_position(self, position_ms: int, length_ms: int) -> None:
        """Sync slider and labels; ignored while the user is dragging."""
        self._length_ms = length_ms
        self.duration_label.setText(format_time(length_ms))
        if self._seeking:
            return
        self.time_label.setText(format_time(position_ms))
        if length_ms > 0:
            ratio = position_ms / length_ms
            blocked = self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(int(ratio * self.seek_slider.maximum()))
            self.seek_slider.blockSignals(blocked)

    # ----------------------------------------------------------------- private
    def _on_speed_changed(self, index: int) -> None:
        self.speed_changed.emit(float(self.speed_combo.itemData(index)))

    def _on_seek_pressed(self) -> None:
        self._seeking = True

    def _on_seek_moved(self, value: int) -> None:
        # Live-update the elapsed label as the user drags.
        if self._length_ms > 0:
            ratio = value / self.seek_slider.maximum()
            self.time_label.setText(format_time(int(ratio * self._length_ms)))

    def _on_seek_released(self) -> None:
        self._seeking = False
        if self._length_ms > 0:
            ratio = self.seek_slider.value() / self.seek_slider.maximum()
            self.seek_requested.emit(int(ratio * self._length_ms))
