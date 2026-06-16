"""Presentation rendering: themes and the python-pptx builder."""

from .builder import render_deck
from .themes import THEMES, Theme, get_theme

__all__ = ["render_deck", "THEMES", "Theme", "get_theme"]
