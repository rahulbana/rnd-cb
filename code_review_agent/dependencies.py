"""Resolve definitions of the functions/methods a file depends on.

Reviewing a file in isolation misses whole classes of bugs: calling a function
with the wrong number/type of arguments, mishandling its return value, or
relying on a callee that is itself unsafe. This module builds a lightweight,
regex-based symbol index across the project, works out which symbols a file
calls, and returns their definitions so they can be supplied to the reviewer as
context.

The extraction is heuristic (no full parser) so it degrades gracefully: for an
unknown language it simply finds nothing and the feature adds no context.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .collector import (
    DEFAULT_IGNORE_DIRS,
    extensions_for,
    normalize_language,
)

# Languages whose blocks are delimited by indentation rather than braces.
_INDENT_LANGS = {"python"}

# Names that must never be treated as a call target or a definition name.
_KEYWORDS: Set[str] = {
    "if", "for", "while", "switch", "catch", "else", "return", "do", "with",
    "function", "func", "def", "class", "new", "typeof", "sizeof", "and", "or",
    "not", "in", "is", "await", "yield", "throw", "case", "elif", "when",
    "match", "select", "go", "defer", "print", "println",
}

# Very common built-ins / stdlib calls that are never worth resolving.
_CALL_STOPWORDS: Set[str] = {
    "len", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "range", "enumerate", "zip", "map", "filter", "open", "super", "isinstance",
    "getattr", "setattr", "hasattr", "format", "join", "split", "append",
    "get", "set", "add", "remove", "pop", "keys", "values", "items", "strip",
    "log", "error", "warn", "info", "debug", "assert", "require", "type",
}

# Per-language definition header patterns. Each captures a ``name`` group.
_DEF_PATTERNS: Dict[str, List[Tuple[str, "re.Pattern[str]"]]] = {
    "python": [
        ("function", re.compile(r"^(?P<indent>\s*)(?:async\s+)?def\s+(?P<name>\w+)\s*\(")),
        ("class", re.compile(r"^(?P<indent>\s*)class\s+(?P<name>\w+)\b")),
    ],
    "javascript": [
        ("function", re.compile(r"^(?P<indent>\s*)(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s+(?P<name>\w+)\s*\(")),
        ("function", re.compile(r"^(?P<indent>\s*)(?:export\s+)?(?:const|let|var)\s+(?P<name>\w+)\s*=\s*(?:async\s*)?(?:function|\([^;=]*\)\s*=>|\w+\s*=>)")),
        ("class", re.compile(r"^(?P<indent>\s*)(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(?P<name>\w+)\b")),
        ("method", re.compile(r"^(?P<indent>\s+)(?:static\s+|async\s+|get\s+|set\s+)*(?P<name>\w+)\s*\([^)]*\)\s*\{")),
    ],
    "go": [
        ("function", re.compile(r"^func\s+(?:\([^)]*\)\s*)?(?P<name>\w+)\s*[\(\[]")),
    ],
    "rust": [
        ("function", re.compile(r"^(?P<indent>\s*)(?:pub\s+)?(?:async\s+)?fn\s+(?P<name>\w+)\s*[<(]")),
        ("struct", re.compile(r"^(?P<indent>\s*)(?:pub\s+)?(?:struct|enum|trait)\s+(?P<name>\w+)\b")),
    ],
    "php": [
        ("function", re.compile(r"^(?P<indent>\s*)(?:public|private|protected|static|abstract|final|\s)*function\s+(?P<name>\w+)\s*\(")),
        ("class", re.compile(r"^(?P<indent>\s*)(?:abstract\s+|final\s+)?class\s+(?P<name>\w+)\b")),
    ],
    "ruby": [
        ("function", re.compile(r"^(?P<indent>\s*)def\s+(?:self\.)?(?P<name>\w+)")),
        ("class", re.compile(r"^(?P<indent>\s*)(?:class|module)\s+(?P<name>\w+)\b")),
    ],
    "kotlin": [
        ("function", re.compile(r"^(?P<indent>\s*)(?:[\w@]+\s+)*fun\s+(?:<[^>]+>\s*)?(?P<name>\w+)\s*[(<]")),
        ("class", re.compile(r"^(?P<indent>\s*)(?:[\w@]+\s+)*(?:class|object|interface)\s+(?P<name>\w+)\b")),
    ],
    "swift": [
        ("function", re.compile(r"^(?P<indent>\s*)(?:[\w@]+\s+)*func\s+(?P<name>\w+)\s*[(<]")),
        ("class", re.compile(r"^(?P<indent>\s*)(?:[\w@]+\s+)*(?:class|struct|enum|protocol)\s+(?P<name>\w+)\b")),
    ],
    # C-family languages share a method/function-with-body heuristic.
    "java": [
        ("class", re.compile(r"^(?P<indent>\s*)(?:[\w@]+\s+)*(?:class|interface|enum)\s+(?P<name>\w+)\b")),
        ("method", re.compile(r"^(?P<indent>\s*)(?:@\w+\s*)*(?:public|private|protected|static|final|abstract|synchronized|native|default|\s)+[\w<>\[\],\.\s]+?\s+(?P<name>\w+)\s*\([^;{)]*\)\s*(?:throws [\w,\.\s]+)?\{")),
    ],
    "csharp": [
        ("class", re.compile(r"^(?P<indent>\s*)(?:[\w@]+\s+)*(?:class|interface|struct|enum)\s+(?P<name>\w+)\b")),
        ("method", re.compile(r"^(?P<indent>\s*)(?:\[[^\]]*\]\s*)*(?:public|private|protected|internal|static|virtual|override|abstract|async|sealed|\s)+[\w<>\[\],\.\s]+?\s+(?P<name>\w+)\s*\([^;{)]*\)\s*\{")),
    ],
    "c": [
        ("function", re.compile(r"^(?P<indent>[\w:<>\*&\s]+?)\s+(?P<name>\w+)\s*\([^;{)]*\)\s*\{")),
    ],
    "cpp": [
        ("function", re.compile(r"^(?P<indent>[\w:<>\*&\s]+?)\s+(?P<name>\w+)\s*\([^;{)]*\)\s*(?:const\s*)?\{")),
        ("class", re.compile(r"^(?P<indent>\s*)(?:class|struct)\s+(?P<name>\w+)\b")),
    ],
    "scala": [
        ("function", re.compile(r"^(?P<indent>\s*)(?:[\w@]+\s+)*def\s+(?P<name>\w+)\s*[(\[:]")),
        ("class", re.compile(r"^(?P<indent>\s*)(?:[\w@]+\s+)*(?:class|object|trait)\s+(?P<name>\w+)\b")),
    ],
}
# TypeScript shares JavaScript's grammar for our purposes.
_DEF_PATTERNS["typescript"] = _DEF_PATTERNS["javascript"]

# Detect call sites: ``name(`` and ``.method(``.
_CALL_RE = re.compile(r"(?:(?<=\.)|(?<![\w.]))(?P<name>[A-Za-z_]\w*)\s*\(")

_MAX_DEF_LINES = 60  # cap how much of a definition body we capture


@dataclass
class Definition:
    """A single function/method/class definition discovered in the project."""

    name: str
    kind: str
    file: str
    start_line: int
    end_line: int
    snippet: str


SymbolIndex = Dict[str, List[Definition]]


def _patterns_for(language: str):
    return _DEF_PATTERNS.get(normalize_language(language), [])


def _block_end(lines: List[str], start: int, language: str) -> int:
    """Return the exclusive end index of the block starting at ``lines[start]``."""

    cap = min(len(lines), start + _MAX_DEF_LINES)
    if normalize_language(language) in _INDENT_LANGS:
        base = len(lines[start]) - len(lines[start].lstrip())
        for j in range(start + 1, len(lines)):
            line = lines[j]
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= base:
                return min(j, cap)
        return cap

    # Brace-based: balance braces starting from the first '{' near the header.
    depth = 0
    seen_brace = False
    for j in range(start, len(lines)):
        depth += lines[j].count("{") - lines[j].count("}")
        if "{" in lines[j]:
            seen_brace = True
        if seen_brace and depth <= 0:
            return min(j + 1, cap)
        if j - start >= _MAX_DEF_LINES:
            break
    return start + 1 if not seen_brace else cap


def extract_definitions(path: str, language: str, content: str) -> List[Definition]:
    """Extract top-level and method definitions from a single file."""

    patterns = _patterns_for(language)
    if not patterns:
        return []

    lines = content.splitlines()
    defs: List[Definition] = []
    for i, line in enumerate(lines):
        for kind, pattern in patterns:
            m = pattern.match(line)
            if not m:
                continue
            name = m.group("name")
            if name in _KEYWORDS:
                continue
            end = _block_end(lines, i, language)
            snippet_lines = lines[i:end]
            if len(snippet_lines) >= _MAX_DEF_LINES:
                snippet_lines = snippet_lines[:_MAX_DEF_LINES] + ["    # ... (truncated)"]
            defs.append(
                Definition(
                    name=name,
                    kind=kind,
                    file=path,
                    start_line=i + 1,
                    end_line=end,
                    snippet="\n".join(snippet_lines),
                )
            )
            break  # one definition kind per line is enough
    return defs


def build_symbol_index(
    sources: Iterable[Tuple[str, str, str]]
) -> SymbolIndex:
    """Build ``name -> [Definition, ...]`` from ``(path, language, content)``."""

    index: SymbolIndex = {}
    for path, language, content in sources:
        for definition in extract_definitions(path, language, content):
            index.setdefault(definition.name, []).append(definition)
    return index


def find_call_names(content: str, language: str) -> Set[str]:
    """Return the set of identifiers that appear to be called in ``content``."""

    names: Set[str] = set()
    for m in _CALL_RE.finditer(content):
        name = m.group("name")
        if name in _KEYWORDS or name in _CALL_STOPWORDS:
            continue
        names.add(name)
    return names


def resolve_dependencies(
    *,
    file_path: str,
    language: str,
    content: str,
    index: SymbolIndex,
    max_defs: int = 12,
    max_chars: int = 6000,
) -> List[Definition]:
    """Return definitions (from other files) of the symbols ``content`` calls.

    Same-file definitions are skipped because they are already visible to the
    reviewer. Results are bounded by ``max_defs`` and a total ``max_chars``
    budget to keep prompt size under control.
    """

    called = find_call_names(content, language)
    seen: Set[Tuple[str, str, int]] = set()
    resolved: List[Definition] = []
    budget = 0

    for name in sorted(called):
        for definition in index.get(name, []):
            if os.path.abspath(definition.file) == os.path.abspath(file_path):
                continue  # already visible in the reviewed file
            key = (definition.name, definition.file, definition.start_line)
            if key in seen:
                continue
            seen.add(key)
            cost = len(definition.snippet)
            if resolved and budget + cost > max_chars:
                continue
            resolved.append(definition)
            budget += cost
            if len(resolved) >= max_defs:
                return resolved
    return resolved


# Dependency-manifest files worth showing the reviewer for package-level checks.
_MANIFEST_NAMES: Set[str] = {
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.in",
    "dev-requirements.txt",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "poetry.lock",
    "constraints.txt",
}


def collect_manifests(
    context_dir: Optional[str],
    *,
    max_chars: int = 4000,
    max_depth: int = 2,
) -> List[Tuple[str, str]]:
    """Find dependency-manifest files near ``context_dir`` for package checks.

    Only shallow directories are scanned (manifests live near the project root)
    and the combined content is bounded by ``max_chars``.
    """

    if not context_dir:
        return []
    root = context_dir if os.path.isdir(context_dir) else os.path.dirname(context_dir)
    if not root or not os.path.isdir(root):
        return []

    found: List[Tuple[str, str]] = []
    budget = 0
    root_depth = root.rstrip(os.sep).count(os.sep)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]
        if dirpath.rstrip(os.sep).count(os.sep) - root_depth > max_depth:
            dirs[:] = []
            continue
        for name in sorted(files):
            if name not in _MANIFEST_NAMES and not name.startswith("requirements"):
                continue
            full = os.path.join(dirpath, name)
            try:
                with open(full, "r", encoding="utf-8") as handle:
                    content = handle.read()
            except (OSError, UnicodeDecodeError):
                continue
            remaining = max_chars - budget
            if remaining <= 0:
                return found
            if len(content) > remaining:
                content = content[:remaining] + "\n# ... (truncated)"
            found.append((full, content))
            budget += len(content)
    return found


def iter_source_files(
    root: str,
    language: str,
    *,
    max_files: int = 400,
    max_bytes: int = 400_000,
) -> Iterable[Tuple[str, str]]:
    """Yield ``(path, content)`` for source files under ``root`` (for indexing)."""

    exts = extensions_for(language)
    if not os.path.isdir(root):
        return

    count = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if exts and ext not in exts:
                continue
            full = os.path.join(dirpath, name)
            try:
                if os.path.getsize(full) > max_bytes:
                    continue
                with open(full, "r", encoding="utf-8") as handle:
                    yield full, handle.read()
            except (OSError, UnicodeDecodeError):
                continue
            count += 1
            if count >= max_files:
                return
