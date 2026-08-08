"""Playlist model and widget.

``Playlist`` holds the ordered list of items and the current index; the
``PlaylistWidget`` is a thin ``QListWidget`` view over it that lets the user
reorder, remove, and double-click to play.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem

from .utils import display_name


@dataclass
class PlaylistItem:
    """A single entry: the resource to play plus a display label."""

    mrl: str          # media resource locator handed to VLC (path or URL)
    title: str        # label shown in the list
    source: str       # the original path/URL the user provided
    needs_resolve: bool = False  # True for site URLs pending yt-dlp resolution


class Playlist:
    """Ordered collection of playlist items with a current-index cursor."""

    def __init__(self) -> None:
        self._items: List[PlaylistItem] = []
        self._index: int = -1
        self.repeat: bool = False
        self.shuffle: bool = False

    def __len__(self) -> int:
        return len(self._items)

    @property
    def items(self) -> List[PlaylistItem]:
        return self._items

    @property
    def index(self) -> int:
        return self._index

    def current(self) -> Optional[PlaylistItem]:
        if 0 <= self._index < len(self._items):
            return self._items[self._index]
        return None

    def add(self, item: PlaylistItem) -> int:
        self._items.append(item)
        return len(self._items) - 1

    def remove(self, position: int) -> None:
        if not 0 <= position < len(self._items):
            return
        self._items.pop(position)
        if position < self._index:
            self._index -= 1
        elif position == self._index:
            # Keep the cursor pointing at the following item (or clamp).
            self._index = min(self._index, len(self._items) - 1)

    def clear(self) -> None:
        self._items.clear()
        self._index = -1

    def set_index(self, position: int) -> Optional[PlaylistItem]:
        if 0 <= position < len(self._items):
            self._index = position
            return self._items[position]
        return None

    def next(self) -> Optional[PlaylistItem]:
        if not self._items:
            return None
        if self.shuffle:
            return self._random()
        nxt = self._index + 1
        if nxt >= len(self._items):
            if self.repeat:
                nxt = 0
            else:
                return None
        return self.set_index(nxt)

    def previous(self) -> Optional[PlaylistItem]:
        if not self._items:
            return None
        if self.shuffle:
            return self._random()
        prev = self._index - 1
        if prev < 0:
            if self.repeat:
                prev = len(self._items) - 1
            else:
                return None
        return self.set_index(prev)

    def _random(self) -> Optional[PlaylistItem]:
        import random

        if len(self._items) == 1:
            return self.set_index(0)
        choices = [i for i in range(len(self._items)) if i != self._index]
        return self.set_index(random.choice(choices))


class PlaylistWidget(QListWidget):
    """List view of a :class:`Playlist`.

    Emits ``play_requested`` with the row index when an item is activated.
    """

    play_requested = Signal(int)
    remove_requested = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.itemDoubleClicked.connect(self._on_double_click)

    def rebuild(self, playlist: Playlist) -> None:
        """Redraw all rows from the model and highlight the current one."""
        self.clear()
        for i, item in enumerate(playlist.items):
            entry = QListWidgetItem(item.title or display_name(item.source))
            entry.setToolTip(item.source)
            if i == playlist.index:
                font = entry.font()
                font.setBold(True)
                entry.setFont(font)
            self.addItem(entry)
        if 0 <= playlist.index < self.count():
            self.setCurrentRow(playlist.index)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            row = self.currentRow()
            if row >= 0:
                self.remove_requested.emit(row)
                return
        super().keyPressEvent(event)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        self.play_requested.emit(self.row(item))
