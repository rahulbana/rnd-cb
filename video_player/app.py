"""Application entry point: create the Qt app and show the main window."""

from __future__ import annotations

import sys
from typing import List, Optional

from PySide6.QtWidgets import QApplication, QMessageBox

from . import __app_name__


def _check_vlc() -> Optional[str]:
    """Return an error string if libvlc/python-vlc is unavailable, else None."""
    try:
        import vlc  # noqa: F401
    except (ImportError, OSError) as exc:
        return (
            "Could not load VLC.\n\n"
            "This player needs both the 'python-vlc' package and a VLC "
            "installation (libvlc) on your system.\n\n"
            "Install VLC from https://www.videolan.org/vlc/ and run:\n"
            "    pip install python-vlc\n\n"
            f"Details: {exc}"
        )
    return None


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)

    # Fusion is a consistent base for our custom dark stylesheet across OSes.
    from PySide6.QtWidgets import QStyleFactory

    from .theme import stylesheet

    if "Fusion" in QStyleFactory.keys():
        app.setStyle("Fusion")
    app.setStyleSheet(stylesheet())

    vlc_error = _check_vlc()
    if vlc_error:
        QMessageBox.critical(None, __app_name__, vlc_error)
        return 1

    # Imported after the VLC check so a missing libvlc yields a friendly
    # dialog instead of an import traceback.
    from .main_window import MainWindow

    window = MainWindow()
    window.show()

    # Queue any file/URL arguments onto the playlist and start playing.
    media_args = [arg for arg in argv[1:] if not arg.startswith("-")]
    if media_args:
        for arg in media_args:
            window._enqueue(arg)
        window._refresh_playlist()
        window.play_index(0)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
