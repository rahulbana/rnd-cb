#!/usr/bin/env python3
"""Launch AutoDev.

This starts the always-on FastAPI engine and opens the local web UI in your
browser. The engine keeps running (and keeps building) even if you close the
browser tab — reopen it any time to see live progress.

    python run.py
"""
from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn

from autodev.config import get_settings


def _open_browser(url: str) -> None:
    time.sleep(1.2)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    settings = get_settings()
    url = f"http://{settings.host}:{settings.port}"
    print(f"\n  AutoDev is starting on {url}")
    print(f"  LLM provider: {settings.llm_provider}\n")

    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    uvicorn.run(
        "autodev.main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
