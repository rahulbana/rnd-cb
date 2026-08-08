"""Map file names to QScintilla lexers for syntax highlighting.

The lookup is intentionally forgiving: an unknown extension yields ``None``
and the editor simply shows unhighlighted plain text.
"""
from __future__ import annotations

import os
from typing import Optional


# Extension (without the dot, lowercased) -> QsciLexer* class name.
_EXT_TO_LEXER: dict[str, str] = {
    "py": "QsciLexerPython",
    "pyw": "QsciLexerPython",
    "js": "QsciLexerJavaScript",
    "mjs": "QsciLexerJavaScript",
    "jsx": "QsciLexerJavaScript",
    "ts": "QsciLexerJavaScript",
    "tsx": "QsciLexerJavaScript",
    "json": "QsciLexerJSON",
    "html": "QsciLexerHTML",
    "htm": "QsciLexerHTML",
    "xml": "QsciLexerXML",
    "css": "QsciLexerCSS",
    "scss": "QsciLexerCSS",
    "c": "QsciLexerCPP",
    "h": "QsciLexerCPP",
    "cpp": "QsciLexerCPP",
    "cc": "QsciLexerCPP",
    "cxx": "QsciLexerCPP",
    "hpp": "QsciLexerCPP",
    "java": "QsciLexerJava",
    "cs": "QsciLexerCSharp",
    "sh": "QsciLexerBash",
    "bash": "QsciLexerBash",
    "zsh": "QsciLexerBash",
    "sql": "QsciLexerSQL",
    "md": "QsciLexerMarkdown",
    "markdown": "QsciLexerMarkdown",
    "yaml": "QsciLexerYAML",
    "yml": "QsciLexerYAML",
    "rb": "QsciLexerRuby",
    "pl": "QsciLexerPerl",
    "lua": "QsciLexerLua",
    "tex": "QsciLexerTeX",
    "bat": "QsciLexerBatch",
    "cmd": "QsciLexerBatch",
    "ini": "QsciLexerProperties",
    "cfg": "QsciLexerProperties",
    "conf": "QsciLexerProperties",
    "properties": "QsciLexerProperties",
    "toml": "QsciLexerProperties",
    "diff": "QsciLexerDiff",
    "patch": "QsciLexerDiff",
    "m": "QsciLexerMatlab",
    "f": "QsciLexerFortran",
    "f90": "QsciLexerFortran",
    "pas": "QsciLexerPascal",
    "vhd": "QsciLexerVHDL",
    "vhdl": "QsciLexerVHDL",
    "tcl": "QsciLexerTCL",
    "ps1": "QsciLexerPO",  # PowerShell has no dedicated lexer; leave plain
}

# Bare filenames (no extension) that still map to a language.
_NAME_TO_LEXER: dict[str, str] = {
    "makefile": "QsciLexerMakefile",
    "gnumakefile": "QsciLexerMakefile",
    "dockerfile": "QsciLexerBash",
    "cmakelists.txt": "QsciLexerCMake",
}


def lexer_class_name_for(path_or_name: str) -> Optional[str]:
    """Return the QsciLexer class name for ``path_or_name`` or ``None``."""
    base = os.path.basename(path_or_name).lower()
    if base in _NAME_TO_LEXER:
        return _NAME_TO_LEXER[base]
    _root, ext = os.path.splitext(base)
    ext = ext.lstrip(".")
    return _EXT_TO_LEXER.get(ext)


def make_lexer(path_or_name: str, font=None):
    """Instantiate the matching QsciLexer, or ``None`` when unmapped.

    Import of ``PyQt6.Qsci`` happens lazily so this module stays importable in
    environments without a display (e.g. for unit tests).
    """
    class_name = lexer_class_name_for(path_or_name)
    if class_name is None:
        return None
    try:
        from PyQt6 import Qsci
    except ImportError:
        return None
    lexer_cls = getattr(Qsci, class_name, None)
    if lexer_cls is None:
        return None
    lexer = lexer_cls()
    if font is not None:
        lexer.setDefaultFont(font)
        lexer.setFont(font)
    return lexer
