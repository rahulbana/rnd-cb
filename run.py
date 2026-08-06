#!/usr/bin/env python3
"""Entry point for the AI Agent desktop application.

Usage:
    python run.py            # launch the native desktop window (pywebview)
    python run.py --web      # run the server only and open in your browser
    python run.py --server   # run the server only, no window (for dev/tests)
"""
from __future__ import annotations

import argparse
import sys
import threading
import time

import uvicorn

from app.config import config
from app.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger("run")


def _run_server() -> None:
    # log_config=None stops uvicorn from calling logging.config.dictConfig(),
    # which would otherwise close/detach our application log handlers. We manage
    # logging ourselves via app.logging_config.
    uvicorn.run(
        "app.server:app",
        host=config.HOST,
        port=config.PORT,
        log_level="info",
        log_config=None,
    )


def _start_server_thread() -> threading.Thread:
    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()
    # Give uvicorn a moment to bind the port before we point a window at it.
    time.sleep(1.5)
    return thread


def launch_desktop() -> None:
    """Launch the native desktop window wrapping the local server."""
    try:
        import webview
    except ImportError:
        print("pywebview is not installed. Falling back to browser mode.\n"
              "Install it with: pip install pywebview", file=sys.stderr)
        return launch_web()

    _start_server_thread()
    webview.create_window(
        "AI Agent",
        config.base_url,
        width=1200,
        height=820,
        min_size=(720, 560),
    )
    webview.start()


def launch_web() -> None:
    """Run the server and open the default browser."""
    import webbrowser

    _start_server_thread()
    print(f"AI Agent running at {config.base_url}")
    webbrowser.open(config.base_url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down.")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Agent desktop app")
    parser.add_argument("--web", action="store_true",
                        help="Run server and open in browser instead of a window.")
    parser.add_argument("--server", action="store_true",
                        help="Run the server only (no window/browser).")
    args = parser.parse_args()

    if not config.llm_configured():
        print("⚠️  OpenAI is selected but OPENAI_API_KEY is not set. Add it to .env,\n"
              "    or set LLM_PROVIDER=ollama to run a local model. Direct tools still work.\n",
              file=sys.stderr)
    else:
        print(f"LLM provider: {config.active_provider()} (model: {config.active_model()})",
              file=sys.stderr)

    if args.server:
        _run_server()
    elif args.web:
        launch_web()
    else:
        launch_desktop()


if __name__ == "__main__":
    main()
