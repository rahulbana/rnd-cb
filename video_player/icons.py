"""Crisp, theme-colored icons rendered from inline SVG.

Using SVG keeps the icons sharp at any size and lets us tint them to match the
theme (and brighten them on hover) instead of relying on the platform's dated
stock icons. Rendered pixmaps are cached per (name, color, size).
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Material-style 24x24 path data for each icon.
_PATHS = {
    "play": "M8 5v14l11-7z",
    "pause": "M6 5h4v14H6zM14 5h4v14h-4z",
    "stop": "M6 6h12v12H6z",
    "prev": "M6 6h2v12H6zm3.5 6l8.5 6V6z",
    "next": "M6 18l8.5-6L6 6v12zM16 6h2v12h-2z",
    "volume": (
        "M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 "
        "2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 "
        "6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"
    ),
    "muted": (
        "M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm"
        "2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28"
        "-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l"
        "5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 "
        "3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"
    ),
    "fullscreen": (
        "M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2"
        "V5h-5z"
    ),
    "fullscreen_exit": (
        "M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5"
        "V8h-3z"
    ),
}


def _svg(path: str, color: str) -> bytes:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        f'<path fill="{color}" d="{path}"/></svg>'
    ).encode("utf-8")


@lru_cache(maxsize=256)
def _pixmap(name: str, color: str, size: int) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(_svg(_PATHS[name], color)))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


def icon(name: str, color: str = "#d6d9df", hover: str = "#ffffff", size: int = 40) -> QIcon:
    """A two-state icon: ``color`` normally, ``hover`` when the mouse is over."""
    result = QIcon()
    result.addPixmap(_pixmap(name, color, size), QIcon.Normal)
    result.addPixmap(_pixmap(name, hover, size), QIcon.Active)
    return result
