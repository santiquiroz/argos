"""PyInstaller entry point. Opens the browser, then runs the server (see argos/__main__.py)."""

from __future__ import annotations

import threading
import webbrowser

import uvicorn

from argos.config import get_settings


def _open_browser(port: int) -> None:
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()


def main() -> None:
    settings = get_settings()
    print(f"Argos API key: {settings.api_key}")  # noqa: T201
    print(f"Open http://localhost:{settings.port}")  # noqa: T201
    _open_browser(settings.port)
    uvicorn.run("argos.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
