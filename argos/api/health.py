"""Health + capability report (public; no API key required)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from argos import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict:
    state = request.app.state
    analyzers = [
        {"name": a.name, "available": a.available} for a in getattr(state, "crop_analyzers", [])
    ]
    return {
        "status": "ok",
        "version": __version__,
        "device": state.settings.device,
        "ingest": state.settings.ingest,
        "pipeline_running": getattr(state, "pipeline_task", None) is not None,
        "analyzers": analyzers,
    }
