"""Run blocking cloud calls off the GUI thread.

Cloud authentication (especially OneDrive's device-code flow) and network I/O
can block for seconds; doing that on the Qt main thread would freeze the UI.
:class:`CloudWorker` runs a single callable on a ``QThread`` and reports back
with ``finished`` (result) or ``failed`` (exception message).
"""
from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class CloudWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn: Callable[..., Any], *args, **kwargs) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # noqa: BLE001 - report any failure to the UI
            self.failed.emit(str(exc))
        else:
            self.finished.emit(result)


def run_async(parent, fn, on_success, on_error, *args, **kwargs):
    """Execute ``fn`` in a worker thread and route the outcome to callbacks.

    Returns the ``(thread, worker)`` pair; the caller should keep a reference
    alive (typically on the host widget) until completion so they are not
    garbage-collected mid-run.
    """
    thread = QThread(parent)
    worker = CloudWorker(fn, *args, **kwargs)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(on_success)
    worker.failed.connect(on_error)

    # Tear the thread down once either signal fires.
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread, worker
