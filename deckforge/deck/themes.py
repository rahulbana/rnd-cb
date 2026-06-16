"""Colour palettes and typography for the deck renderer.

Each :class:`Theme` is a self-contained art-direction spec: a background, a
pair of accent colours for shapes/highlights, and the fonts used for
headings vs. body. Add a new look by appending one entry to ``THEMES``.
"""

from __future__ import annotations

from dataclasses import dataclass

from pptx.dml.color import RGBColor


def _rgb(hex_str: str) -> RGBColor:
    return RGBColor.from_string(hex_str.lstrip("#"))


@dataclass(frozen=True)
class Theme:
    name: str
    background: RGBColor      # Slide background
    surface: RGBColor         # Cards / panels sitting on the background
    primary: RGBColor         # Dominant accent
    secondary: RGBColor       # Secondary accent (gradients, alt bars)
    text: RGBColor            # Body text on background
    muted: RGBColor           # Subtitles / captions
    heading_font: str
    body_font: str


# A curated set of high-contrast, "enterprise but creative" palettes.
_THEME_LIST = [
    Theme(
        name="midnight",
        background=_rgb("0F172A"),
        surface=_rgb("1E293B"),
        primary=_rgb("38BDF8"),
        secondary=_rgb("A855F7"),
        text=_rgb("F8FAFC"),
        muted=_rgb("94A3B8"),
        heading_font="Montserrat",
        body_font="Segoe UI",
    ),
    Theme(
        name="sunset",
        background=_rgb("1A1423"),
        surface=_rgb("2D1B3D"),
        primary=_rgb("FB7185"),
        secondary=_rgb("FBBF24"),
        text=_rgb("FFF7ED"),
        muted=_rgb("D8B4A0"),
        heading_font="Poppins",
        body_font="Segoe UI",
    ),
    Theme(
        name="ocean",
        background=_rgb("F0F9FF"),
        surface=_rgb("FFFFFF"),
        primary=_rgb("0EA5E9"),
        secondary=_rgb("14B8A6"),
        text=_rgb("0F2A3F"),
        muted=_rgb("5B7A8C"),
        heading_font="Montserrat",
        body_font="Calibri",
    ),
    Theme(
        name="forest",
        background=_rgb("0B1F17"),
        surface=_rgb("14342A"),
        primary=_rgb("34D399"),
        secondary=_rgb("FACC15"),
        text=_rgb("F0FDF4"),
        muted=_rgb("9CC5B0"),
        heading_font="Poppins",
        body_font="Segoe UI",
    ),
    Theme(
        name="mono",
        background=_rgb("FFFFFF"),
        surface=_rgb("F4F4F5"),
        primary=_rgb("18181B"),
        secondary=_rgb("6366F1"),
        text=_rgb("18181B"),
        muted=_rgb("71717A"),
        heading_font="Georgia",
        body_font="Calibri",
    ),
]

THEMES = {t.name: t for t in _THEME_LIST}


def get_theme(name: str) -> Theme:
    """Return a theme by name, falling back to 'midnight'."""
    return THEMES.get(name.lower(), THEMES["midnight"])
