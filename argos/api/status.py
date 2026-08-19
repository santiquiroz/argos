"""System status: device, VRAM, CPU/RAM, uptime, and activity counts."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from argos.core.devices import make_probe

router = APIRouter(tags=["status"])


def _system_load() -> dict:
    try:
        import psutil  # noqa: PLC0415

        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": psutil.virtual_memory().percent,
        }
    except Exception:  # noqa: BLE001 - psutil is optional
        return {"cpu_percent": None, "ram_percent": None}


@router.get("/status")
def status(request: Request) -> dict:
    state = request.app.state
    settings = state.settings
    probe = make_probe(settings.device)
    started_at = getattr(state, "started_at", time.time())
    return {
        "device": settings.device,
        "ingest": settings.ingest,
        "uptime_s": int(time.time() - started_at),
        "vram_free_mb": probe.free_mb(),
        **_system_load(),
        "cameras": len(state.cameras.list()),
        "zones": len(state.zones.list()),
        **state.store.stats(),
    }
