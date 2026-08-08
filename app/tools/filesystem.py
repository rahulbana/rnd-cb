"""File system tool, sandboxed to a single workspace directory.

Every path the model supplies is resolved and checked to be inside
``WORKSPACE_DIR``; anything that escapes (``../``, absolute paths, symlinks)
is rejected. This lets the agent keep notes, export query results, and read
files back without giving it access to the whole disk.
"""

from __future__ import annotations

from pathlib import Path

from .base import Tool, ToolRegistry

_MAX_READ_BYTES = 200_000


def register(registry: ToolRegistry, config) -> None:
    root = config.workspace_path
    root.mkdir(parents=True, exist_ok=True)

    def _resolve(rel_path: str) -> Path:
        """Resolve a user path and ensure it stays within the sandbox."""
        candidate = (root / rel_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError(
                f"path '{rel_path}' is outside the workspace sandbox"
            )
        return candidate

    def list_dir(path: str = ".") -> str:
        target = _resolve(path)
        if not target.exists():
            return f"Path not found: {path}"
        if target.is_file():
            return f"{path} is a file ({target.stat().st_size} bytes)."
        entries = []
        for child in sorted(target.iterdir()):
            kind = "dir " if child.is_dir() else "file"
            size = child.stat().st_size if child.is_file() else "-"
            entries.append(f"[{kind}] {child.name} ({size})")
        return "\n".join(entries) if entries else "(empty directory)"

    def read_file(path: str) -> str:
        target = _resolve(path)
        if not target.is_file():
            return f"File not found: {path}"
        data = target.read_bytes()
        if len(data) > _MAX_READ_BYTES:
            data = data[:_MAX_READ_BYTES]
            suffix = f"\n... (truncated at {_MAX_READ_BYTES} bytes)"
        else:
            suffix = ""
        try:
            return data.decode("utf-8") + suffix
        except UnicodeDecodeError:
            return f"Cannot display '{path}': binary file ({len(data)} bytes)."

    def write_file(path: str, content: str, append: bool = False) -> str:
        target = _resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(target, mode, encoding="utf-8") as fh:
            fh.write(content)
        action = "Appended to" if append else "Wrote"
        return f"{action} {path} ({len(content)} chars)."

    def delete_file(path: str) -> str:
        target = _resolve(path)
        if not target.exists():
            return f"Nothing to delete at: {path}"
        if target.is_dir():
            return f"Refusing to delete directory '{path}'. Only files can be deleted."
        target.unlink()
        return f"Deleted {path}."

    registry.register(
        Tool(
            name="fs_list_dir",
            description="List files and folders inside the workspace sandbox.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path, default '.'.", "default": "."}
                },
                "additionalProperties": False,
            },
            handler=list_dir,
        )
    )
    registry.register(
        Tool(
            name="fs_read_file",
            description="Read a UTF-8 text file from the workspace sandbox.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative file path."}},
                "required": ["path"],
                "additionalProperties": False,
            },
            handler=read_file,
        )
    )
    registry.register(
        Tool(
            name="fs_write_file",
            description=(
                "Create or overwrite (or append to) a text file in the workspace "
                "sandbox. Useful for saving reports, notes, or exported data."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                    "content": {"type": "string", "description": "Text to write."},
                    "append": {"type": "boolean", "description": "Append instead of overwrite.", "default": False},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            handler=write_file,
        )
    )
    registry.register(
        Tool(
            name="fs_delete_file",
            description="Delete a file inside the workspace sandbox.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative file path."}},
                "required": ["path"],
                "additionalProperties": False,
            },
            handler=delete_file,
        )
    )
