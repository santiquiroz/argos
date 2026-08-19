"""API-key auth middleware. LAN-only posture: a single shared key, constant-time compared.

Public paths (health, docs, and the SPA itself) bypass the check; everything under ``/api`` else
requires the ``X-API-Key`` header.
"""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_PUBLIC_PREFIXES = ("/api/health", "/docs", "/openapi.json", "/redoc")


def _is_public(path: str) -> bool:
    if not path.startswith("/api"):
        return True  # SPA / static assets
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str) -> None:
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if _is_public(request.url.path):
            return await call_next(request)
        provided = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(provided, self._api_key):
            return JSONResponse({"detail": "invalid or missing API key"}, status_code=401)
        return await call_next(request)
