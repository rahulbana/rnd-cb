"""The PyTextEdit main window: tabs, menus, and file/cloud actions."""
from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
)

from . import __app_name__, __version__
from .cloud.base import CloudFile
from .cloud.manager import CloudManager
from .config import (
    GOOGLE_CLIENT_SECRET_FILE,
    ONEDRIVE_CONFIG_FILE,
    Settings,
)
from .editor.editor_widget import CloudRef, EditorWidget
from .ui.cloud_dialog import CloudBrowserDialog
from .ui.find_replace import FindReplaceDialog
from .ui.worker import run_async


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings()
        self.cloud = CloudManager()
        self._async_refs: list[tuple] = []  # keep worker threads alive

        self.setWindowTitle(__app_name__)
        self.resize(1000, 700)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

        self.find_dialog = FindReplaceDialog(self.current_editor, self)

        self._build_menus()
        self._build_statusbar()
        self._apply_theme(self.settings.get("theme", "light"))

        self.new_tab()

    # ------------------------------------------------------------------ tabs
    def current_editor(self) -> Optional[EditorWidget]:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, EditorWidget) else None

    def new_tab(self, title: str = "Untitled") -> EditorWidget:
        editor = EditorWidget(self.settings)
        editor.modificationChanged.connect(
            lambda _modified, ed=editor: self._update_tab_title(ed)
        )
        editor.cursorPositionChanged.connect(self._update_cursor_status)
        editor.textChanged.connect(self._update_status_counts)
        index = self.tabs.addTab(editor, title)
        self.tabs.setCurrentIndex(index)
        editor.setFocus()
        return editor

    def _tab_label(self, editor: EditorWidget) -> str:
        if editor.file_path:
            name = os.path.basename(editor.file_path)
        elif editor.cloud_ref:
            name = editor.cloud_ref.name
        else:
            name = "Untitled"
        return ("• " if editor.is_modified else "") + name

    def _update_tab_title(self, editor: EditorWidget) -> None:
        index = self.tabs.indexOf(editor)
        if index >= 0:
            self.tabs.setTabText(index, self._tab_label(editor))
            tip = editor.file_path or (
                f"{editor.cloud_ref.provider_id}:{editor.cloud_ref.name}"
                if editor.cloud_ref
                else ""
            )
            self.tabs.setTabToolTip(index, tip)
        self._update_window_title()

    def _update_window_title(self) -> None:
        editor = self.current_editor()
        if editor is None:
            self.setWindowTitle(__app_name__)
            return
        label = self._tab_label(editor).lstrip("• ")
        star = "• " if editor.is_modified else ""
        self.setWindowTitle(f"{star}{label} — {__app_name__}")

    def _close_tab(self, index: int) -> None:
        editor = self.tabs.widget(index)
        if isinstance(editor, EditorWidget) and not self._maybe_save(editor):
            return
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.new_tab()

    def _on_tab_changed(self, _index: int) -> None:
        self._update_window_title()
        self._update_cursor_status()
        self._update_status_counts()
        self._sync_language_label()

    # --------------------------------------------------------------- menus
    def _build_menus(self) -> None:
        menubar = self.menuBar()

        # -- File -----------------------------------------------------------
        file_menu = menubar.addMenu("&File")
        self._add_action(file_menu, "&New", self.new_tab, QKeySequence.StandardKey.New)
        self._add_action(file_menu, "&Open…", self.open_file, QKeySequence.StandardKey.Open)
        self.recent_menu = file_menu.addMenu("Open &Recent")
        self._rebuild_recent_menu()
        file_menu.addSeparator()
        self._add_action(file_menu, "&Save", self.save_file, QKeySequence.StandardKey.Save)
        self._add_action(
            file_menu, "Save &As…", self.save_file_as, QKeySequence.StandardKey.SaveAs
        )
        file_menu.addSeparator()
        self._add_action(
            file_menu, "&Close Tab", self.close_current_tab, QKeySequence.StandardKey.Close
        )
        self._add_action(file_menu, "E&xit", self.close, QKeySequence.StandardKey.Quit)

        # -- Edit -----------------------------------------------------------
        edit_menu = menubar.addMenu("&Edit")
        self._add_action(edit_menu, "&Undo", self._edit_undo, QKeySequence.StandardKey.Undo)
        self._add_action(edit_menu, "&Redo", self._edit_redo, QKeySequence.StandardKey.Redo)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Cu&t", self._edit_cut, QKeySequence.StandardKey.Cut)
        self._add_action(edit_menu, "&Copy", self._edit_copy, QKeySequence.StandardKey.Copy)
        self._add_action(edit_menu, "&Paste", self._edit_paste, QKeySequence.StandardKey.Paste)
        self._add_action(
            edit_menu, "Select &All", self._edit_select_all, QKeySequence.StandardKey.SelectAll
        )
        edit_menu.addSeparator()
        self._add_action(
            edit_menu, "&Find/Replace…", self.find_dialog.open_for_search,
            QKeySequence.StandardKey.Find,
        )

        # -- View -----------------------------------------------------------
        view_menu = menubar.addMenu("&View")
        self.wrap_action = self._add_checkable(
            view_menu, "&Word Wrap", self._toggle_word_wrap,
            checked=bool(self.settings.get("word_wrap", False)),
        )
        self.ws_action = self._add_checkable(
            view_menu, "Show &Whitespace", self._toggle_whitespace,
            checked=bool(self.settings.get("show_whitespace", False)),
        )
        view_menu.addSeparator()
        self._add_action(view_menu, "Zoom &In", self._zoom_in, QKeySequence.StandardKey.ZoomIn)
        self._add_action(view_menu, "Zoom &Out", self._zoom_out, QKeySequence.StandardKey.ZoomOut)
        self._add_action(view_menu, "&Reset Zoom", self._zoom_reset, "Ctrl+0")
        view_menu.addSeparator()
        theme_menu = view_menu.addMenu("&Theme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        for name in ("light", "dark"):
            action = QAction(name.capitalize(), self, checkable=True)
            action.setChecked(self.settings.get("theme", "light") == name)
            action.triggered.connect(lambda _c, n=name: self._apply_theme(n))
            theme_group.addAction(action)
            theme_menu.addAction(action)

        # -- Cloud ----------------------------------------------------------
        cloud_menu = menubar.addMenu("&Cloud")
        for provider in self.cloud.providers():
            sub = cloud_menu.addMenu(provider.name)
            if not provider.is_available():
                info = QAction("(dependencies not installed)", self)
                info.setEnabled(False)
                sub.addAction(info)
            open_action = QAction(f"Open from {provider.name}…", self)
            open_action.triggered.connect(lambda _c, p=provider.id: self.open_from_cloud(p))
            sub.addAction(open_action)
            save_action = QAction(f"Save to {provider.name}…", self)
            save_action.triggered.connect(lambda _c, p=provider.id: self.save_to_cloud(p))
            sub.addAction(save_action)
            sub.addSeparator()
            signout_action = QAction("Sign out", self)
            signout_action.triggered.connect(lambda _c, p=provider.id: self._sign_out(p))
            sub.addAction(signout_action)
        cloud_menu.addSeparator()
        self._add_action(cloud_menu, "Where are my credentials stored?", self._show_cred_paths)

        # -- Help -----------------------------------------------------------
        help_menu = menubar.addMenu("&Help")
        self._add_action(help_menu, "&About", self._show_about)

    def _add_action(self, menu, text, slot, shortcut=None) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(lambda _checked=False: slot())
        menu.addAction(action)
        return action

    def _add_checkable(self, menu, text, slot, checked=False) -> QAction:
        action = QAction(text, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(lambda c: slot(c))
        menu.addAction(action)
        return action

    def _rebuild_recent_menu(self) -> None:
        self.recent_menu.clear()
        recent = self.settings.get("recent_files", [])
        if not recent:
            empty = QAction("(no recent files)", self)
            empty.setEnabled(False)
            self.recent_menu.addAction(empty)
            return
        for path in recent:
            action = QAction(path, self)
            action.triggered.connect(lambda _c, p=path: self._open_path(p))
            self.recent_menu.addAction(action)

    # --------------------------------------------------------------- status
    def _build_statusbar(self) -> None:
        self.status = self.statusBar()
        self.cursor_label = QLabel("Ln 1, Col 1")
        self.count_label = QLabel("0 chars")
        self.language_label = QLabel("Plain Text")
        self.encoding_label = QLabel("UTF-8")
        for widget in (self.cursor_label, self.count_label,
                       self.language_label, self.encoding_label):
            self.status.addPermanentWidget(widget)

    def _update_cursor_status(self) -> None:
        editor = self.current_editor()
        if editor is None:
            return
        line, col = editor.getCursorPosition()
        self.cursor_label.setText(f"Ln {line + 1}, Col {col + 1}")

    def _update_status_counts(self) -> None:
        editor = self.current_editor()
        if editor is None:
            return
        text = editor.content()
        self.count_label.setText(f"{len(text)} chars, {editor.lines()} lines")

    def _sync_language_label(self) -> None:
        editor = self.current_editor()
        if editor is None:
            return
        lexer = editor.lexer()
        self.language_label.setText(lexer.language() if lexer else "Plain Text")

    # ------------------------------------------------------------ edit slots
    def _edit_undo(self):
        if e := self.current_editor():
            e.undo()

    def _edit_redo(self):
        if e := self.current_editor():
            e.redo()

    def _edit_cut(self):
        if e := self.current_editor():
            e.cut()

    def _edit_copy(self):
        if e := self.current_editor():
            e.copy()

    def _edit_paste(self):
        if e := self.current_editor():
            e.paste()

    def _edit_select_all(self):
        if e := self.current_editor():
            e.selectAll()

    # ------------------------------------------------------------ view slots
    def _toggle_word_wrap(self, checked: bool) -> None:
        self.settings.set("word_wrap", checked)
        self.settings.save()
        for editor in self._all_editors():
            editor.set_word_wrap(checked)

    def _toggle_whitespace(self, checked: bool) -> None:
        self.settings.set("show_whitespace", checked)
        self.settings.save()
        for editor in self._all_editors():
            editor.set_show_whitespace(checked)

    def _zoom_in(self):
        if e := self.current_editor():
            e.zoom_in_step()

    def _zoom_out(self):
        if e := self.current_editor():
            e.zoom_out_step()

    def _zoom_reset(self):
        if e := self.current_editor():
            e.zoom_reset()

    def _apply_theme(self, name: str) -> None:
        self.settings.set("theme", name)
        self.settings.save()
        for editor in self._all_editors():
            editor.apply_theme(name)
        self._apply_window_theme(name)
        self._sync_language_label()

    def _apply_window_theme(self, name: str) -> None:
        if name == "dark":
            self.setStyleSheet(
                "QMainWindow, QMenuBar, QMenu, QStatusBar, QTabWidget::pane, "
                "QTabBar::tab { background: #252526; color: #dcdcdc; }"
                "QMenuBar::item:selected, QMenu::item:selected { background: #094771; }"
                "QTabBar::tab:selected { background: #1e1e1e; }"
            )
        else:
            self.setStyleSheet("")

    def _all_editors(self):
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, EditorWidget):
                yield widget

    # ------------------------------------------------------------ file I/O
    def open_file(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(self, "Open File")
        if path:
            self._open_path(path)

    def _open_path(self, path: str) -> None:
        # If already open, just focus that tab.
        for editor in self._all_editors():
            if editor.file_path == path:
                self.tabs.setCurrentWidget(editor)
                return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            QMessageBox.critical(self, "Open failed", str(exc))
            return

        editor = self._target_editor_for_open()
        editor.file_path = path
        editor.cloud_ref = None
        editor.set_content(content)
        editor.refresh_lexer()
        self._update_tab_title(editor)
        self._sync_language_label()
        self.settings.add_recent_file(path)
        self.settings.save()
        self._rebuild_recent_menu()

    def _target_editor_for_open(self) -> EditorWidget:
        """Reuse the current tab if it is a pristine 'Untitled', else new one."""
        editor = self.current_editor()
        if (
            editor is not None
            and editor.file_path is None
            and editor.cloud_ref is None
            and not editor.is_modified
            and not editor.content().strip()
        ):
            return editor
        return self.new_tab()

    def save_file(self) -> bool:
        editor = self.current_editor()
        if editor is None:
            return False
        if editor.file_path:
            return self._write_local(editor, editor.file_path)
        if editor.cloud_ref:
            # Cloud-backed document: re-upload in place.
            self._upload_existing(editor)
            return True
        return self.save_file_as()

    def save_file_as(self) -> bool:
        editor = self.current_editor()
        if editor is None:
            return False
        start = editor.file_path or ""
        path, _filter = QFileDialog.getSaveFileName(self, "Save File As", start)
        if not path:
            return False
        if self._write_local(editor, path):
            editor.file_path = path
            editor.cloud_ref = None
            editor.refresh_lexer()
            self._update_tab_title(editor)
            self._sync_language_label()
            self.settings.add_recent_file(path)
            self.settings.save()
            self._rebuild_recent_menu()
            return True
        return False

    def _write_local(self, editor: EditorWidget, path: str) -> bool:
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(editor.content())
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return False
        editor.setModified(False)
        self._update_tab_title(editor)
        self.status.showMessage(f"Saved {path}", 4000)
        return True

    def close_current_tab(self) -> None:
        self._close_tab(self.tabs.currentIndex())

    def _maybe_save(self, editor: EditorWidget) -> bool:
        """Prompt to save a modified document. Return False to cancel close."""
        if not editor.is_modified:
            return True
        name = self._tab_label(editor).lstrip("• ")
        choice = QMessageBox.question(
            self,
            "Unsaved changes",
            f"Save changes to '{name}' before closing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if choice == QMessageBox.StandardButton.Save:
            self.tabs.setCurrentWidget(editor)
            return self.save_file()
        if choice == QMessageBox.StandardButton.Discard:
            return True
        return False

    # ------------------------------------------------------------ cloud I/O
    def _keep_async(self, refs) -> None:
        """Retain worker/thread refs and prune finished ones."""
        self._async_refs.append(refs)
        self._async_refs = [
            (t, w) for (t, w) in self._async_refs if t is not None and t.isRunning()
        ]

    def open_from_cloud(self, provider_id: str) -> None:
        provider = self.cloud.get(provider_id)
        if provider is None:
            return
        if not provider.is_available():
            self._deps_message(provider_id)
            return
        dialog = CloudBrowserDialog(provider, mode="open", parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted or dialog.selected_file is None:
            return
        cloud_file: CloudFile = dialog.selected_file
        self.status.showMessage(f"Downloading {cloud_file.name}…")

        def done(content: bytes):
            editor = self._target_editor_for_open()
            editor.file_path = None
            editor.cloud_ref = CloudRef(provider_id, cloud_file.id, cloud_file.name)
            editor.set_content(content.decode("utf-8", errors="replace"))
            editor.refresh_lexer()
            self._update_tab_title(editor)
            self._sync_language_label()
            self.status.showMessage(f"Opened {cloud_file.name} from {provider.name}", 4000)

        self._keep_async(
            run_async(self, provider.download, done, self._cloud_error, cloud_file.id)
        )

    def save_to_cloud(self, provider_id: str) -> None:
        provider = self.cloud.get(provider_id)
        editor = self.current_editor()
        if provider is None or editor is None:
            return
        if not provider.is_available():
            self._deps_message(provider_id)
            return
        suggested = ""
        if editor.file_path:
            suggested = os.path.basename(editor.file_path)
        elif editor.cloud_ref:
            suggested = editor.cloud_ref.name
        dialog = CloudBrowserDialog(
            provider, mode="save", suggested_name=suggested, parent=self
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        name = dialog.selected_name
        folder_id = dialog.selected_folder_id
        content = editor.content().encode("utf-8")
        self.status.showMessage(f"Uploading {name}…")

        def done(cloud_file: CloudFile):
            editor.file_path = None
            editor.cloud_ref = CloudRef(provider_id, cloud_file.id, cloud_file.name)
            editor.setModified(False)
            editor.refresh_lexer()
            self._update_tab_title(editor)
            self._sync_language_label()
            self.status.showMessage(f"Saved {cloud_file.name} to {provider.name}", 4000)

        self._keep_async(
            run_async(
                self, provider.upload, done, self._cloud_error,
                name, content, None, folder_id,
            )
        )

    def _upload_existing(self, editor: EditorWidget) -> None:
        ref = editor.cloud_ref
        provider = self.cloud.get(ref.provider_id)
        if provider is None:
            return
        content = editor.content().encode("utf-8")
        self.status.showMessage(f"Uploading {ref.name}…")

        def done(cloud_file: CloudFile):
            editor.setModified(False)
            self._update_tab_title(editor)
            self.status.showMessage(f"Saved {cloud_file.name} to {provider.name}", 4000)

        self._keep_async(
            run_async(
                self, provider.upload, done, self._cloud_error,
                ref.name, content, ref.file_id, None,
            )
        )

    def _cloud_error(self, message: str) -> None:
        self.status.clearMessage()
        QMessageBox.critical(self, "Cloud error", message)

    def _sign_out(self, provider_id: str) -> None:
        provider = self.cloud.get(provider_id)
        if provider is None:
            return
        provider.sign_out()
        self.status.showMessage(f"Signed out of {provider.name}", 4000)

    def _deps_message(self, provider_id: str) -> None:
        pkgs = {
            "gdrive": "google-api-python-client google-auth-oauthlib",
            "onedrive": "msal requests",
        }.get(provider_id, "")
        QMessageBox.information(
            self,
            "Optional dependency missing",
            f"This provider needs extra packages:\n\n    pip install {pkgs}",
        )

    def _show_cred_paths(self) -> None:
        QMessageBox.information(
            self,
            "Credential locations",
            "Place your OAuth credentials here:\n\n"
            f"Google Drive client secret:\n{GOOGLE_CLIENT_SECRET_FILE}\n\n"
            f"OneDrive config:\n{ONEDRIVE_CONFIG_FILE}\n\n"
            "See the README for how to obtain them.",
        )

    # --------------------------------------------------------------- about
    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {__app_name__}",
            f"<h3>{__app_name__} {__version__}</h3>"
            "<p>A Notepad++-style text editor built with PyQt6 and QScintilla, "
            "with direct save to Google Drive and OneDrive.</p>",
        )

    # --------------------------------------------------------------- close
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        for editor in list(self._all_editors()):
            if not self._maybe_save(editor):
                event.ignore()
                return
        event.accept()
