"""``python -m argos`` — run the server."""

from __future__ import annotations

import uvicorn

from argos.config import get_settings


def main() -> None:
    settings = get_settings()
    print(f"Argos API key: {settings.api_key}")  # noqa: T201 - first-run convenience
    uvicorn.run("argos.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
