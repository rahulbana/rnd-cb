"""Tests for the desktop (pywebview) bridge.

The native window and dialogs are mocked, so these tests exercise the real
filesystem read/write/export logic and the menu wiring without launching a GUI.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from markdown_editor import desktop
from markdown_editor.desktop import DesktopApi


class FakeWindow:
    """Stand-in for webview.Window that scripts dialog return values."""

    def __init__(self, dialog_result=None):
        self.dialog_result = dialog_result
        self.evaluated = []

    def create_file_dialog(self, *args, **kwargs):
        return self.dialog_result

    def evaluate_js(self, script):
        self.evaluated.append(script)


def test_is_desktop_and_app_info():
    api = DesktopApi()
    assert api.is_desktop() is True
    info = api.app_info()
    assert "version" in info and "platform" in info


def test_read_path(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("# Title\n", encoding="utf-8")
    api = DesktopApi()
    res = api.read_path(str(f))
    assert res == {"path": str(f), "name": "note", "content": "# Title\n"}


def test_write_path_roundtrip(tmp_path):
    api = DesktopApi()
    target = tmp_path / "out.md"
    res = api.write_path(str(target), "hello")
    assert res == {"path": str(target), "name": "out"}
    assert target.read_text(encoding="utf-8") == "hello"


def test_write_path_adds_md_extension(tmp_path):
    api = DesktopApi()
    target = tmp_path / "noext"
    res = api.write_path(str(target), "x")
    assert res["path"].endswith(".md")
    assert (tmp_path / "noext.md").read_text(encoding="utf-8") == "x"


def test_open_dialog_reads_selected_file(tmp_path):
    f = tmp_path / "pick.md"
    f.write_text("picked", encoding="utf-8")
    api = DesktopApi()
    api.attach(FakeWindow(dialog_result=(str(f),)))
    res = api.open_dialog()
    assert res["content"] == "picked"
    assert res["name"] == "pick"


def test_open_dialog_cancel_returns_none():
    api = DesktopApi()
    api.attach(FakeWindow(dialog_result=None))
    assert api.open_dialog() is None


def test_save_dialog_writes_content(tmp_path):
    target = tmp_path / "saved.md"
    api = DesktopApi()
    api.attach(FakeWindow(dialog_result=str(target)))
    res = api.save_dialog("body text", suggested="saved")
    assert res == {"path": str(target), "name": "saved"}
    assert target.read_text(encoding="utf-8") == "body text"


def test_save_dialog_cancel_returns_none():
    api = DesktopApi()
    api.attach(FakeWindow(dialog_result=None))
    assert api.save_dialog("x") is None


def test_export_html_writes_standalone_document(tmp_path):
    target = tmp_path / "page.html"
    api = DesktopApi()
    api.attach(FakeWindow(dialog_result=str(target)))
    res = api.export_html("# Heading", title="Page")
    assert res == {"path": str(target)}
    html = target.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert "<h1" in html


def test_export_html_adds_extension(tmp_path):
    target = tmp_path / "page"  # no extension
    api = DesktopApi()
    api.attach(FakeWindow(dialog_result=str(target)))
    res = api.export_html("x", title="Page")
    assert res["path"].endswith(".html")


def test_build_menu_structure():
    window = FakeWindow()
    menus = desktop.build_menu(window)
    titles = [m.title for m in menus]
    assert titles == ["File", "Edit", "View", "Help"]


def test_menu_action_invokes_frontend():
    from webview.menu import Menu, MenuAction

    window = FakeWindow()
    menus = desktop.build_menu(window)
    file_menu = menus[0]
    # Find the "New" action and fire its callback.
    new_action = next(
        item for item in file_menu.items if isinstance(item, MenuAction) and item.title == "New"
    )
    new_action.function()
    assert any("MDEditor" in s and "newDoc" in s for s in window.evaluated)
