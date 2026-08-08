"""Console entry point: ``python -m pytextedit`` (or the ``pytextedit`` script)."""
from __future__ import annotations

import sys


def main() -> int:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        sys.stderr.write(
            "PyTextEdit requires PyQt6 and QScintilla.\n"
            "Install them with:\n\n"
            "    pip install PyQt6 PyQt6-QScintilla\n"
        )
        return 1

    # Import the window only after confirming Qt is present, so the message
    # above is what users without the GUI stack actually see.
    from .app import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("PyTextEdit")
    window = MainWindow()

    # Open any file paths passed on the command line.
    for path in sys.argv[1:]:
        window._open_path(path)  # noqa: SLF001 - intentional internal use

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
