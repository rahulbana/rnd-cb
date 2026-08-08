"""A non-modal Find/Replace dialog driven by QScintilla's search API."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class FindReplaceDialog(QDialog):
    """Search and replace within the currently active editor.

    The dialog holds no editor reference of its own; instead it asks the host
    window for the active editor each time, so it keeps working as the user
    switches tabs.
    """

    def __init__(self, get_editor, parent=None) -> None:
        super().__init__(parent)
        self._get_editor = get_editor
        self.setWindowTitle("Find and Replace")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._build_ui()

    def _build_ui(self) -> None:
        grid = QGridLayout(self)

        grid.addWidget(QLabel("Find:"), 0, 0)
        self.find_edit = QLineEdit()
        self.find_edit.returnPressed.connect(self.find_next)
        grid.addWidget(self.find_edit, 0, 1)

        grid.addWidget(QLabel("Replace:"), 1, 0)
        self.replace_edit = QLineEdit()
        grid.addWidget(self.replace_edit, 1, 1)

        options = QWidget()
        opt_layout = QHBoxLayout(options)
        opt_layout.setContentsMargins(0, 0, 0, 0)
        self.case_box = QCheckBox("Match case")
        self.word_box = QCheckBox("Whole word")
        self.regex_box = QCheckBox("Regex")
        self.wrap_box = QCheckBox("Wrap around")
        self.wrap_box.setChecked(True)
        for box in (self.case_box, self.word_box, self.regex_box, self.wrap_box):
            opt_layout.addWidget(box)
        grid.addWidget(options, 2, 0, 1, 2)

        buttons = QWidget()
        btn_layout = QHBoxLayout(buttons)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        find_btn = QPushButton("Find Next")
        find_btn.clicked.connect(self.find_next)
        replace_btn = QPushButton("Replace")
        replace_btn.clicked.connect(self.replace_current)
        replace_all_btn = QPushButton("Replace All")
        replace_all_btn.clicked.connect(self.replace_all)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        for btn in (find_btn, replace_btn, replace_all_btn, close_btn):
            btn_layout.addWidget(btn)
        grid.addWidget(buttons, 3, 0, 1, 2)

        self.status = QLabel("")
        grid.addWidget(self.status, 4, 0, 1, 2)

    # -- actions ------------------------------------------------------------
    def open_for_search(self) -> None:
        editor = self._get_editor()
        if editor is not None and editor.hasSelectedText():
            self.find_edit.setText(editor.selectedText())
        self.find_edit.setFocus()
        self.find_edit.selectAll()
        self.show()
        self.raise_()
        self.activateWindow()

    def find_next(self) -> bool:
        editor = self._get_editor()
        if editor is None:
            return False
        text = self.find_edit.text()
        if not text:
            return False
        found = editor.findFirst(
            text,
            self.regex_box.isChecked(),
            self.case_box.isChecked(),
            self.word_box.isChecked(),
            self.wrap_box.isChecked(),
        )
        self.status.setText("" if found else "No matches found.")
        return found

    def replace_current(self) -> None:
        editor = self._get_editor()
        if editor is None:
            return
        if editor.hasSelectedText():
            editor.replace(self.replace_edit.text())
        self.find_next()

    def replace_all(self) -> None:
        editor = self._get_editor()
        if editor is None:
            return
        text = self.find_edit.text()
        if not text:
            return
        count = 0
        # Start from the top of the document for a deterministic sweep.
        found = editor.findFirst(
            text,
            self.regex_box.isChecked(),
            self.case_box.isChecked(),
            self.word_box.isChecked(),
            False,   # do not wrap: sweep once from the start
            True,    # forward
            0,
            0,
        )
        while found:
            editor.replace(self.replace_edit.text())
            count += 1
            found = editor.findNext()
        self.status.setText(f"Replaced {count} occurrence(s).")
