"""A single editable document: a QScintilla view plus its file/cloud origin."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QColor, QFont

from .lexers import make_lexer


@dataclass
class CloudRef:
    """Identifies where a document lives in the cloud, if anywhere."""

    provider_id: str
    file_id: str
    name: str


# Colours for the two built-in themes: (paper, text, margin bg, margin fg,
# caret-line, selection bg).
_THEMES = {
    "light": {
        "paper": "#ffffff",
        "text": "#1e1e1e",
        "margin_bg": "#f0f0f0",
        "margin_fg": "#808080",
        "caret_line": "#f5f5f0",
        "selection": "#cce8ff",
    },
    "dark": {
        "paper": "#1e1e1e",
        "text": "#dcdcdc",
        "margin_bg": "#2a2a2a",
        "margin_fg": "#858585",
        "caret_line": "#2d2d2d",
        "selection": "#264f78",
    },
}


class EditorWidget(QsciScintilla):
    """One tab's worth of editor with source-code niceties enabled."""

    def __init__(self, settings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.file_path: Optional[str] = None
        self.cloud_ref: Optional[CloudRef] = None
        self.encoding = "utf-8"
        # QScintilla only stores a C++ pointer to the lexer, so we must keep a
        # Python reference ourselves or it gets garbage-collected immediately.
        self._lexer_ref = None

        self._font = QFont(
            settings.get("font_family", "Monospace"),
            int(settings.get("font_size", 11)),
        )
        self._font.setFixedPitch(True)
        self.setFont(self._font)

        self._configure_common()
        self.apply_theme(settings.get("theme", "light"))
        self.set_word_wrap(bool(settings.get("word_wrap", False)))
        self.set_show_whitespace(bool(settings.get("show_whitespace", False)))

    # -- one-time editor configuration --------------------------------------
    def _configure_common(self) -> None:
        self.setUtf8(True)

        # Line-number margin (margin 0), auto-sized to the document length.
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginLineNumbers(0, True)
        self.setMarginWidth(0, "0000")

        # Folding margin for languages whose lexer supports it.
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)

        # Indentation.
        self.setIndentationsUseTabs(not bool(self._settings.get("use_spaces", True)))
        self.setTabWidth(int(self._settings.get("tab_width", 4)))
        self.setAutoIndent(True)
        self.setIndentationGuides(True)
        self.setBackspaceUnindents(True)

        # Editing aids.
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setCaretLineVisible(True)
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsDocument)
        self.setAutoCompletionThreshold(3)
        self.setEolMode(QsciScintilla.EolMode.EolUnix)

    # -- theming ------------------------------------------------------------
    def apply_theme(self, theme_name: str) -> None:
        theme = _THEMES.get(theme_name, _THEMES["light"])
        paper = QColor(theme["paper"])
        text = QColor(theme["text"])

        self.setColor(text)
        self.setPaper(paper)
        self.setMarginsBackgroundColor(QColor(theme["margin_bg"]))
        self.setMarginsForegroundColor(QColor(theme["margin_fg"]))
        self.setCaretLineBackgroundColor(QColor(theme["caret_line"]))
        self.setSelectionBackgroundColor(QColor(theme["selection"]))
        self.setCaretForegroundColor(text)
        self.setMatchedBraceBackgroundColor(QColor(theme["selection"]))

        # Re-apply the lexer so its own colours refresh under the new theme.
        self._current_theme = theme_name
        if self.file_path or (self.cloud_ref and self.cloud_ref.name):
            self.refresh_lexer()
        else:
            self.setLexer(None)
            self.setColor(text)
            self.setPaper(paper)

    # -- lexer / language ---------------------------------------------------
    def refresh_lexer(self) -> None:
        """Pick and apply the lexer that matches the current file name."""
        name = self.file_path or (self.cloud_ref.name if self.cloud_ref else "")
        if not name:
            self._lexer_ref = None
            self.setLexer(None)
            return
        lexer = make_lexer(name, self._font)
        theme = _THEMES.get(getattr(self, "_current_theme", "light"))
        if lexer is not None:
            # Give the lexer a sensible default paper so it blends with theme.
            lexer.setPaper(QColor(theme["paper"]))
            lexer.setDefaultPaper(QColor(theme["paper"]))
            # Retain the reference before handing the pointer to Scintilla.
            self._lexer_ref = lexer
            self.setLexer(lexer)
        else:
            self._lexer_ref = None
            self.setLexer(None)
            self.setColor(QColor(theme["text"]))
            self.setPaper(QColor(theme["paper"]))

    # -- view options -------------------------------------------------------
    def set_word_wrap(self, enabled: bool) -> None:
        mode = (
            QsciScintilla.WrapMode.WrapWord
            if enabled
            else QsciScintilla.WrapMode.WrapNone
        )
        self.setWrapMode(mode)

    def set_show_whitespace(self, enabled: bool) -> None:
        mode = (
            QsciScintilla.WhitespaceVisibility.WsVisible
            if enabled
            else QsciScintilla.WhitespaceVisibility.WsInvisible
        )
        self.setWhitespaceVisibility(mode)

    def set_font_size(self, size: int) -> None:
        self._font.setPointSize(max(6, size))
        self.setFont(self._font)
        lexer = self.lexer()
        if lexer is not None:
            lexer.setFont(self._font)
            lexer.setDefaultFont(self._font)

    def zoom_in_step(self) -> None:
        self.zoomIn()

    def zoom_out_step(self) -> None:
        self.zoomOut()

    def zoom_reset(self) -> None:
        self.zoomTo(0)

    # -- document text ------------------------------------------------------
    def set_content(self, text: str) -> None:
        self.setText(text)
        self.setModified(False)

    def content(self) -> str:
        return self.text()

    @property
    def is_modified(self) -> bool:
        return self.isModified()
