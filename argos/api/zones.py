"""Per-camera zone CRUD (normalized 0..1 polygons)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from argos.zones import Zone

router = APIRouter(tags=["zones"])


class ZoneCreate(BaseModel):
    camera: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    kind: Literal["alert", "ignore"] = "alert"
    points: list[tuple[float, float]] = Field(min_length=3)


def _zone_dict(z: Zone) -> dict:
    return {"id": z.id, "camera": z.camera, "name": z.name, "kind": z.kind, "points": z.points}


@router.get("/cameras/{camera}/zones")
def list_zones(camera: str, request: Request) -> list[dict]:
    return [_zone_dict(z) for z in request.app.state.zones.for_camera(camera)]


@router.post("/zones")
def add_zone(body: ZoneCreate, request: Request) -> dict:
    zone = Zone(camera=body.camera, name=body.name, kind=body.kind, points=[tuple(p) for p in body.points])
    request.app.state.zones.add(zone)
    return _zone_dict(zone)


@router.delete("/zones/{zone_id}")
def remove_zone(zone_id: str, request: Request) -> dict:
    if not request.app.state.zones.remove(zone_id):
        raise HTTPException(status_code=404, detail="zone not found")
    return {"removed": zone_id}
