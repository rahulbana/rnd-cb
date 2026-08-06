"""Note management tools: create, list, search, delete (SQLite-backed)."""
from __future__ import annotations

from ..storage import db
from .base import NO_PARAMS, Tool, err, ok


def create_note(title: str, body: str = "", tags: str = "") -> dict:
    """Create a note with a title, optional body and comma-separated tags."""
    if not title.strip():
        return err("A note title is required.")
    note = db.create_note(title.strip(), body, tags)
    return ok(note, message=f"Note #{note['id']} created.")


def list_notes(limit: int = 100) -> dict:
    """List saved notes, most recently updated first."""
    notes = db.list_notes(limit)
    return ok({"count": len(notes), "notes": notes})


def search_notes(query: str, limit: int = 100) -> dict:
    """Search notes by title, body or tags."""
    notes = db.search_notes(query, limit)
    return ok({"query": query, "count": len(notes), "notes": notes})


def delete_note(note_id: int) -> dict:
    """Delete a note by its numeric id."""
    deleted = db.delete_note(int(note_id))
    if not deleted:
        return err(f"No note found with id {note_id}.")
    return ok({"id": note_id}, message=f"Note #{note_id} deleted.")


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="create_note",
            description="Create and save a note with a title, optional body and tags.",
            category="Notes",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title."},
                    "body": {"type": "string", "description": "Note body/content."},
                    "tags": {"type": "string", "description": "Comma-separated tags."},
                },
                "required": ["title"],
            },
            func=create_note,
        ),
        Tool(
            name="list_notes",
            description="List saved notes, most recent first.",
            category="Notes",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max notes (default 100)."},
                },
                "required": [],
            },
            func=list_notes,
        ),
        Tool(
            name="search_notes",
            description="Search saved notes by keyword in title, body or tags.",
            category="Notes",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword."},
                    "limit": {"type": "integer", "description": "Max results (default 100)."},
                },
                "required": ["query"],
            },
            func=search_notes,
        ),
        Tool(
            name="delete_note",
            description="Delete a saved note by its numeric id.",
            category="Notes",
            parameters={
                "type": "object",
                "properties": {
                    "note_id": {"type": "integer", "description": "The note's id."},
                },
                "required": ["note_id"],
            },
            func=delete_note,
        ),
    ]
