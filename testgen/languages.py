"""Language detection and test-file conventions per language.

Maps a source file's extension to its language, the idiomatic test framework,
and how the generated test file should be named / located.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LanguageSpec:
    name: str
    framework: str
    # Given a source path, return the conventional test file path (relative
    # form is handled by the caller / writer).
    test_filename: "callable"  # type: ignore[valid-type]


def _py_test_name(src: Path) -> str:
    return f"test_{src.stem}.py"


def _js_test_name(src: Path) -> str:
    return f"{src.stem}.test{src.suffix}"


def _go_test_name(src: Path) -> str:
    return f"{src.stem}_test.go"


def _java_test_name(src: Path) -> str:
    return f"{src.stem}Test.java"


def _rb_test_name(src: Path) -> str:
    return f"{src.stem}_spec.rb"


def _rs_test_name(src: Path) -> str:
    return f"{src.stem}_test.rs"


def _php_test_name(src: Path) -> str:
    return f"{src.stem}Test.php"


# Extension -> LanguageSpec
_SPECS: dict[str, LanguageSpec] = {
    ".py": LanguageSpec("Python", "pytest", _py_test_name),
    ".js": LanguageSpec("JavaScript", "Jest", _js_test_name),
    ".jsx": LanguageSpec("JavaScript (React)", "Jest + React Testing Library", _js_test_name),
    ".ts": LanguageSpec("TypeScript", "Jest (ts-jest)", _js_test_name),
    ".tsx": LanguageSpec("TypeScript (React)", "Jest + React Testing Library", _js_test_name),
    ".go": LanguageSpec("Go", "the standard testing package", _go_test_name),
    ".java": LanguageSpec("Java", "JUnit 5", _java_test_name),
    ".rb": LanguageSpec("Ruby", "RSpec", _rb_test_name),
    ".rs": LanguageSpec("Rust", "the built-in test harness", _rs_test_name),
    ".php": LanguageSpec("PHP", "PHPUnit", _php_test_name),
}

SUPPORTED_EXTENSIONS = frozenset(_SPECS)


def detect(path: Path) -> LanguageSpec | None:
    """Return the :class:`LanguageSpec` for a file, or ``None`` if unsupported."""
    return _SPECS.get(path.suffix.lower())
