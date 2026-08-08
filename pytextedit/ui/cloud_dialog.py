"""Browse a cloud provider to pick a file to open, or a folder to save into."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..cloud.base import CloudFile, CloudProvider
from .worker import run_async


class CloudBrowserDialog(QDialog):
    """A minimal folder navigator over a :class:`CloudProvider`.

    In ``open`` mode a file selection is returned. In ``save`` mode the user
    navigates to a folder and enters a file name.
    """

    def __init__(
        self, provider: CloudProvider, mode: str = "open",
        suggested_name: str = "", parent=None,
    ) -> None:
        super().__init__(parent)
        self._provider = provider
        self._mode = mode
        self._thread = None  # keep worker refs alive
        self._worker = None

        # Navigation stack of (folder_id, label) with root at the bottom.
        self._stack: list[tuple[Optional[str], str]] = [(None, "Root")]

        self.selected_file: Optional[CloudFile] = None
        self.selected_folder_id: Optional[str] = None
        self.selected_name: str = suggested_name

        self.setWindowTitle(f"{provider.name} — {'Open' if mode == 'open' else 'Save'}")
        self.resize(520, 460)
        self._build_ui(suggested_name)
        self._authenticate_then_list()

    def _build_ui(self, suggested_name: str) -> None:
        layout = QVBoxLayout(self)

        self.path_label = QLabel("Root")
        self.path_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.path_label)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_widget)

        self.status_label = QLabel("Connecting…")
        layout.addWidget(self.status_label)

        if self._mode == "save":
            name_row = QHBoxLayout()
            name_row.addWidget(QLabel("File name:"))
            self.name_edit = QLineEdit(suggested_name)
            name_row.addWidget(self.name_edit)
            layout.addLayout(name_row)

        button_row = QHBoxLayout()
        self.up_btn = QPushButton("Up")
        self.up_btn.clicked.connect(self._go_up)
        button_row.addWidget(self.up_btn)
        button_row.addStretch()

        action_text = "Open" if self._mode == "open" else "Save Here"
        self.action_btn = QPushButton(action_text)
        self.action_btn.clicked.connect(self._on_action)
        button_row.addWidget(self.action_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

    # -- busy-state helpers -------------------------------------------------
    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.list_widget.setEnabled(not busy)
        self.action_btn.setEnabled(not busy)
        self.up_btn.setEnabled(not busy)
        if message:
            self.status_label.setText(message)

    # -- provider interaction ----------------------------------------------
    def _authenticate_then_list(self) -> None:
        self._set_busy(True, "Authenticating…")

        def do_auth():
            if not self._provider.is_authenticated():
                self._provider.authenticate()
            return True

        self._thread, self._worker = run_async(
            self,
            do_auth,
            lambda _ok: self._load_current_folder(),
            self._on_error,
        )

    def _load_current_folder(self) -> None:
        folder_id, label = self._stack[-1]
        self.path_label.setText(" / ".join(lbl for _fid, lbl in self._stack))
        self._set_busy(True, "Loading…")

        self._thread, self._worker = run_async(
            self,
            self._provider.list_files,
            self._on_listed,
            self._on_error,
            folder_id,
        )

    def _on_listed(self, files: list[CloudFile]) -> None:
        self.list_widget.clear()
        for cloud_file in files:
            item = QListWidgetItem(cloud_file.display_name)
            item.setData(Qt.ItemDataRole.UserRole, cloud_file)
            self.list_widget.addItem(item)
        self._set_busy(False, f"{len(files)} item(s).")

    def _on_error(self, message: str) -> None:
        self._set_busy(False, "")
        QMessageBox.critical(self, "Cloud error", message)
        if not self.list_widget.count():
            # Nothing loaded at all — close so the user isn't stuck.
            self.reject()

    # -- navigation ---------------------------------------------------------
    def _current_file(self) -> Optional[CloudFile]:
        item = self.list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_double_click(self, item: QListWidgetItem) -> None:
        cloud_file: CloudFile = item.data(Qt.ItemDataRole.UserRole)
        if cloud_file.is_folder:
            self._stack.append((cloud_file.id, cloud_file.name))
            self._load_current_folder()
        elif self._mode == "open":
            self._choose_file(cloud_file)

    def _go_up(self) -> None:
        if len(self._stack) > 1:
            self._stack.pop()
            self._load_current_folder()

    def _on_action(self) -> None:
        if self._mode == "open":
            cloud_file = self._current_file()
            if cloud_file is None:
                self.status_label.setText("Select a file to open.")
                return
            if cloud_file.is_folder:
                self._stack.append((cloud_file.id, cloud_file.name))
                self._load_current_folder()
                return
            self._choose_file(cloud_file)
        else:
            name = self.name_edit.text().strip()
            if not name:
                self.status_label.setText("Enter a file name.")
                return
            self.selected_name = name
            self.selected_folder_id = self._stack[-1][0]
            self.accept()

    def _choose_file(self, cloud_file: CloudFile) -> None:
        self.selected_file = cloud_file
        self.accept()
