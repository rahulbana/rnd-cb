"""Filesystem and shell tools, sandboxed to the project directory."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

MAX_READ_BYTES = 200_000
MAX_OUTPUT_CHARS = 30_000
DEFAULT_TIMEOUT_S = 60

IGNORED_DIRS = {".git", "node_modules", "dist", "out", ".next", ".venv", "__pycache__", ".cache"}


def _resolve_in_root(root: str, p: str) -> Path:
    """Resolve a path against root and ensure it stays inside the sandbox."""
    root_path = Path(root).resolve()
    candidate = Path(p)
    abs_path = candidate.resolve() if candidate.is_absolute() else (root_path / candidate).resolve()
    if abs_path != root_path and root_path not in abs_path.parents:
        raise ValueError(f'Path "{p}" is outside the project directory.')
    return abs_path


def list_files(root: str, directory: str = ".", max_entries: int = 500) -> str:
    start = _resolve_in_root(root, directory)
    root_path = Path(root).resolve()
    results: list[str] = []

    def walk(current: Path) -> None:
        if len(results) >= max_entries:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda e: e.name)
        except OSError:
            return
        for entry in entries:
            if len(results) >= max_entries:
                break
            if entry.name.startswith(".git"):
                continue
            rel = str(entry.relative_to(root_path))
            if entry.is_dir():
                if entry.name in IGNORED_DIRS:
                    continue
                results.append(rel + os.sep)
                walk(entry)
            else:
                results.append(rel)

    walk(start)
    if not results:
        return "(no files)"
    header = f"(showing first {max_entries} entries)\n" if len(results) >= max_entries else ""
    return header + "\n".join(sorted(results))


def list_dir(root: str, directory: str = ".") -> list[dict]:
    """List the immediate children of a directory (for a lazy file tree).

    Returns dicts of {name, path, type} with directories first, then files,
    each sorted alphabetically. Heavy/vendor dirs and .git are hidden.
    """
    base = _resolve_in_root(root, directory)
    if not base.is_dir():
        raise ValueError(f'"{directory}" is not a directory.')
    root_path = Path(root).resolve()
    items: list[dict] = []
    for entry in sorted(base.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
        if entry.name == ".git":
            continue
        is_dir = entry.is_dir()
        if is_dir and entry.name in IGNORED_DIRS:
            continue
        items.append(
            {
                "name": entry.name,
                "path": str(entry.relative_to(root_path)),
                "type": "dir" if is_dir else "file",
            }
        )
    return items


def read_file(root: str, path: str) -> str:
    abs_path = _resolve_in_root(root, path)
    if abs_path.is_dir():
        raise ValueError(f'"{path}" is a directory.')
    size = abs_path.stat().st_size
    with abs_path.open("r", encoding="utf-8", errors="replace") as fh:
        data = fh.read(MAX_READ_BYTES)
    if size > MAX_READ_BYTES:
        return data + f"\n\n... [truncated: file is {size} bytes]"
    return data


def write_file(root: str, path: str, content: str) -> str:
    abs_path = _resolve_in_root(root, path)
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    rel = abs_path.relative_to(Path(root).resolve())
    return f"Wrote {len(content.encode('utf-8'))} bytes to {rel}"


async def run_command(root: str, command: str, timeout_s: int = DEFAULT_TIMEOUT_S) -> str:
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=root,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        output = stdout.decode("utf-8", errors="replace") if stdout else ""
        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + "\n... [output truncated]"
        return f"Exit code: {proc.returncode}\n\n{output or '(no output)'}"
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return f"Exit code: null\n\n[command timed out after {timeout_s}s]"
