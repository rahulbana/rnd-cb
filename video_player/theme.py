"""Dark theme: an accent color plus a global Qt stylesheet.

Kept in one place so the whole app shares a consistent palette. Widgets opt
into specific styling with object names (e.g. the seek slider vs. the volume
slider, the big play button vs. the flat transport buttons).
"""

from __future__ import annotations

# Palette ------------------------------------------------------------------
ACCENT = "#3d8bfd"          # primary accent (sliders, play button)
ACCENT_HOVER = "#5b9dff"
BG = "#121316"              # window background
SURFACE = "#1b1d22"        # panels / control bar
SURFACE_ALT = "#23262d"    # hovered rows, inputs
BORDER = "#2c2f37"
TEXT = "#e6e8ec"
TEXT_MUTED = "#9aa0aa"


def stylesheet() -> str:
    """Return the application-wide QSS."""
    return f"""
    QWidget {{
        background-color: {BG};
        color: {TEXT};
        font-size: 13px;
        selection-background-color: {ACCENT};
        selection-color: #ffffff;
    }}

    /* ---- Menu bar & menus ------------------------------------------- */
    QMenuBar {{
        background-color: {BG};
        padding: 2px 4px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 6px 12px;
        border-radius: 6px;
    }}
    QMenuBar::item:selected {{ background: {SURFACE_ALT}; }}
    QMenu {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 7px 24px 7px 20px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{ background: {ACCENT}; color: #ffffff; }}
    QMenu::separator {{ height: 1px; background: {BORDER}; margin: 6px 8px; }}

    /* ---- Control bar ----------------------------------------------- */
    #controlBar {{
        background-color: {SURFACE};
        border-top: 1px solid {BORDER};
    }}

    /* Flat transport buttons */
    QToolButton {{
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 6px;
    }}
    QToolButton:hover {{ background: {SURFACE_ALT}; }}
    QToolButton:pressed {{ background: {BORDER}; }}

    /* Big circular accent play button */
    #playButton {{
        background: {ACCENT};
        border-radius: 24px;
        padding: 0px;
        min-width: 48px;
        min-height: 48px;
    }}
    #playButton:hover {{ background: {ACCENT_HOVER}; }}
    #playButton:pressed {{ background: {ACCENT}; }}

    /* ---- Time labels ----------------------------------------------- */
    #timeLabel {{ color: {TEXT_MUTED}; }}

    /* ---- Seek slider ----------------------------------------------- */
    #seekSlider::groove:horizontal {{
        height: 5px;
        border-radius: 2px;
        background: {BORDER};
    }}
    #seekSlider::sub-page:horizontal {{
        height: 5px;
        border-radius: 2px;
        background: {ACCENT};
    }}
    #seekSlider::handle:horizontal {{
        background: #ffffff;
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    #seekSlider::handle:horizontal:hover {{ background: {ACCENT_HOVER}; }}

    /* ---- Volume slider --------------------------------------------- */
    #volumeSlider::groove:horizontal {{
        height: 4px;
        border-radius: 2px;
        background: {BORDER};
    }}
    #volumeSlider::sub-page:horizontal {{
        height: 4px;
        border-radius: 2px;
        background: {TEXT_MUTED};
    }}
    #volumeSlider::handle:horizontal {{
        background: {TEXT};
        width: 11px;
        height: 11px;
        margin: -4px 0;
        border-radius: 5px;
    }}
    #volumeSlider::handle:horizontal:hover {{ background: #ffffff; }}

    /* ---- Speed selector -------------------------------------------- */
    QComboBox {{
        background: {SURFACE_ALT};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 4px 10px;
        min-width: 56px;
    }}
    QComboBox:hover {{ border-color: {ACCENT}; }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 6px;
        selection-background-color: {ACCENT};
        outline: none;
    }}

    /* ---- Playlist dock --------------------------------------------- */
    QDockWidget {{
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}
    QDockWidget::title {{
        background: {SURFACE};
        padding: 8px 12px;
        border-bottom: 1px solid {BORDER};
        font-weight: 600;
    }}
    QListWidget {{
        background: {SURFACE};
        border: none;
        outline: none;
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 9px 10px;
        border-radius: 6px;
        margin: 1px 2px;
    }}
    QListWidget::item:hover {{ background: {SURFACE_ALT}; }}
    QListWidget::item:selected {{ background: {ACCENT}; color: #ffffff; }}

    /* ---- Status bar ------------------------------------------------ */
    QStatusBar {{
        background: {SURFACE};
        border-top: 1px solid {BORDER};
        color: {TEXT_MUTED};
    }}
    QStatusBar::item {{ border: none; }}

    /* ---- Scrollbars ------------------------------------------------ */
    QScrollBar:vertical {{
        background: transparent; width: 10px; margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER}; border-radius: 5px; min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

    /* ---- Dialogs --------------------------------------------------- */
    QLineEdit {{
        background: {SURFACE_ALT};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 7px 10px;
    }}
    QLineEdit:focus {{ border-color: {ACCENT}; }}
    QPushButton {{
        background: {SURFACE_ALT};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 7px 16px;
    }}
    QPushButton:hover {{ background: {BORDER}; }}
    QPushButton:default {{ background: {ACCENT}; border-color: {ACCENT}; color: #fff; }}
    QPushButton:default:hover {{ background: {ACCENT_HOVER}; }}
    """
