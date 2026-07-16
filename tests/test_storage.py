"""Tests for the workspace document storage layer."""

import pytest

from markdown_editor.storage import StorageError, Workspace


@pytest.fixture
def ws(tmp_path):
    return Workspace(tmp_path)


def test_create_read_roundtrip(ws):
    ws.create("Notes", "# Hello")
    doc = ws.read("Notes")
    assert doc.name == "Notes"
    assert doc.content == "# Hello"
    assert doc.size == len("# Hello")


def test_extension_is_stripped(ws):
    ws.create("Notes.md", "x")
    assert ws.exists("Notes")
    assert ws.exists("Notes.md")  # both forms resolve to the same doc


def test_create_duplicate_fails(ws):
    ws.create("Dup", "a")
    with pytest.raises(StorageError):
        ws.create("Dup", "b")


def test_write_overwrites(ws):
    ws.create("Doc", "one")
    ws.write("Doc", "two")
    assert ws.read("Doc").content == "two"


def test_list_sorted_by_mtime(ws):
    import os
    import time

    ws.create("Old", "a")
    time.sleep(0.01)
    ws.create("New", "b")
    names = [d.name for d in ws.list_documents()]
    assert names[0] == "New"
    assert set(names) == {"Old", "New"}


def test_rename(ws):
    ws.create("Before", "hi")
    ws.rename("Before", "After")
    assert not ws.exists("Before")
    assert ws.read("After").content == "hi"


def test_rename_onto_existing_fails(ws):
    ws.create("A", "1")
    ws.create("B", "2")
    with pytest.raises(StorageError):
        ws.rename("A", "B")


def test_delete(ws):
    ws.create("Trash", "x")
    ws.delete("Trash")
    assert not ws.exists("Trash")
    with pytest.raises(StorageError):
        ws.read("Trash")


def test_unique_name(ws):
    assert ws.unique_name("Untitled") == "Untitled"
    ws.create("Untitled", "")
    assert ws.unique_name("Untitled") == "Untitled 2"
    ws.create("Untitled 2", "")
    assert ws.unique_name("Untitled") == "Untitled 3"


@pytest.mark.parametrize("bad", ["../escape", "a/b", "..", "", "   ", "no*star", "pipe|x"])
def test_invalid_names_rejected(ws, bad):
    with pytest.raises(StorageError):
        ws.create(bad, "x")


def test_path_traversal_cannot_escape(ws, tmp_path):
    # Attempting traversal must never touch a file outside the workspace.
    outside = tmp_path.parent / "secret.md"
    outside.write_text("secret")
    with pytest.raises(StorageError):
        ws.read("../secret")
    assert outside.read_text() == "secret"  # untouched


def test_read_missing_raises(ws):
    with pytest.raises(StorageError):
        ws.read("nope")
