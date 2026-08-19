"""Config backup: export/import cameras + zones + settings overrides.

Lets you move an Argos setup between machines. The export contains camera credentials (it's a
restore file) — it's served only to the authenticated admin. It does NOT include the biometric
database (persons/embeddings), which stays on the machine.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from argos import __version__
from argos.cameras import Camera
from argos.settings_store import apply_overrides
from argos.zones import Zone

router = APIRouter(tags=["backup"])


class BackupPayload(BaseModel):
    version: str | None = None
    cameras: list[dict] = []
    zones: list[dict] = []
    settings: dict = {}


@router.get("/backup/export")
def export_backup(request: Request) -> dict:
    state = request.app.state
    return {
        "version": __version__,
        "cameras": [{"name": c.name, "url": c.url, "enabled": c.enabled} for c in state.cameras.list()],
        "zones": [{"camera": z.camera, "name": z.name, "kind": z.kind, "points": z.points} for z in state.zones.list()],
        "settings": state.settings_store.read(),
    }


@router.post("/backup/import")
def import_backup(body: BackupPayload, request: Request) -> dict:
    state = request.app.state
    for cam in body.cameras:
        state.cameras.add(Camera(name=cam["name"], url=cam["url"], enabled=cam.get("enabled", True)))
    for zone in body.zones:
        state.zones.add(Zone(camera=zone["camera"], name=zone["name"], kind=zone.get("kind", "alert"), points=[tuple(p) for p in zone["points"]]))
    if body.settings:
        state.settings_store.update(body.settings)
        apply_overrides(state.settings, body.settings)
    return {"cameras": len(body.cameras), "zones": len(body.zones), "settings": bool(body.settings)}
