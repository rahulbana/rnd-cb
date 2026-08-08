"""Extension-to-lexer mapping (no GUI required)."""
from pytextedit.editor.lexers import lexer_class_name_for


def test_common_extensions():
    cases = {
        "foo.py": "QsciLexerPython",
        "bar.js": "QsciLexerJavaScript",
        "data.json": "QsciLexerJSON",
        "index.html": "QsciLexerHTML",
        "main.cpp": "QsciLexerCPP",
        "notes.md": "QsciLexerMarkdown",
        "config.yaml": "QsciLexerYAML",
    }
    for name, expected in cases.items():
        assert lexer_class_name_for(name) == expected


def test_bare_names():
    assert lexer_class_name_for("Makefile") == "QsciLexerMakefile"
    assert lexer_class_name_for("/proj/Dockerfile") == "QsciLexerBash"


def test_case_insensitive_and_paths():
    assert lexer_class_name_for("/a/b/SCRIPT.PY") == "QsciLexerPython"


def test_unknown_returns_none():
    assert lexer_class_name_for("mystery.zzz") is None
    assert lexer_class_name_for("no_extension") is None
