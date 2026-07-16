"""Workspace document storage.

Documents live as ``.md`` files inside a single workspace directory.  This
module is the only place that touches the filesystem, which keeps path-safety
in one auditable spot: every public function resolves the requested name
against the workspace root and refuses anything that escapes it.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

# Allowed characters in a stored document name (without the extension).  This
# is deliberately conservative — it blocks path separators, ``..`` traversal
# and shell/URL metacharacters.
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9 _.\-()]+$")
_EXT = ".md"


class StorageError(Exception):
    """Raised for invalid names, traversal attempts or missing documents."""


@dataclass
class Document:
    """A stored markdown document and its metadata."""

    name: str          # display name, without extension
    content: str
    modified: float    # epoch seconds
    size: int          # bytes on disk

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DocumentInfo:
    """Lightweight listing entry (no content)."""

    name: str
    modified: float
    size: int

    def to_dict(self) -> dict:
        return asdict(self)


class Workspace:
    """Manage markdown documents under a single root directory."""

    def __init__(self, root: os.PathLike | str):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    # -- name / path validation -------------------------------------------

    def _sanitize(self, name: str) -> str:
        """Normalise a user-supplied name to a bare, extension-less stem."""
        if name is None:
            raise StorageError("A document name is required.")
        name = name.strip()
        if name.lower().endswith(_EXT):
            name = name[: -len(_EXT)]
        name = name.strip()
        if not name:
            raise StorageError("A document name is required.")
        if len(name) > 120:
            raise StorageError("Document name is too long (max 120 characters).")
        if not _SAFE_NAME_RE.match(name):
            raise StorageError(
                "Invalid name. Use letters, numbers, spaces and _ . - ( ) only."
            )
        if name in (".", ".."):
            raise StorageError("Invalid document name.")
        return name

    def _path_for(self, name: str) -> Path:
        stem = self._sanitize(name)
        path = (self.root / f"{stem}{_EXT}").resolve()
        # Defence in depth: even after sanitising, confirm the resolved path
        # is really inside the workspace root.
        if path.parent != self.root:
            raise StorageError("Path escapes the workspace.")
        return path

    # -- queries ----------------------------------------------------------

    def list_documents(self) -> List[DocumentInfo]:
        """Return all documents, most-recently-modified first."""
        infos: List[DocumentInfo] = []
        for entry in self.root.glob(f"*{_EXT}"):
            if not entry.is_file():
                continue
            stat = entry.stat()
            infos.append(
                DocumentInfo(
                    name=entry.stem,
                    modified=stat.st_mtime,
                    size=stat.st_size,
                )
            )
        infos.sort(key=lambda i: i.modified, reverse=True)
        return infos

    def exists(self, name: str) -> bool:
        try:
            return self._path_for(name).is_file()
        except StorageError:
            return False

    def read(self, name: str) -> Document:
        path = self._path_for(name)
        if not path.is_file():
            raise StorageError(f"Document '{name}' does not exist.")
        content = path.read_text(encoding="utf-8")
        stat = path.stat()
        return Document(
            name=path.stem,
            content=content,
            modified=stat.st_mtime,
            size=stat.st_size,
        )

    # -- mutations --------------------------------------------------------

    def write(self, name: str, content: str) -> Document:
        """Create or overwrite a document, writing atomically."""
        path = self._path_for(name)
        tmp = path.with_suffix(_EXT + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)  # atomic on POSIX & Windows
        stat = path.stat()
        return Document(
            name=path.stem,
            content=content,
            modified=stat.st_mtime,
            size=stat.st_size,
        )

    def create(self, name: str, content: str = "") -> Document:
        """Create a new document, failing if one already exists."""
        path = self._path_for(name)
        if path.exists():
            raise StorageError(f"Document '{path.stem}' already exists.")
        return self.write(name, content)

    def unique_name(self, base: str = "Untitled") -> str:
        """Return a name derived from *base* that is not yet taken."""
        base = self._sanitize(base)
        if not self.exists(base):
            return base
        i = 2
        while self.exists(f"{base} {i}"):
            i += 1
        return f"{base} {i}"

    def rename(self, old: str, new: str) -> Document:
        src = self._path_for(old)
        dst = self._path_for(new)
        if not src.is_file():
            raise StorageError(f"Document '{old}' does not exist.")
        if dst.exists() and dst != src:
            raise StorageError(f"Document '{dst.stem}' already exists.")
        os.replace(src, dst)
        return self.read(dst.stem)

    def delete(self, name: str) -> None:
        path = self._path_for(name)
        if not path.is_file():
            raise StorageError(f"Document '{name}' does not exist.")
        path.unlink()


def default_workspace_dir() -> Path:
    """Resolve the workspace directory from the environment or a sane default."""
    env = os.environ.get("MDEDITOR_WORKSPACE")
    if env:
        return Path(env).expanduser()
    return Path.home() / "markdown-editor-docs"
