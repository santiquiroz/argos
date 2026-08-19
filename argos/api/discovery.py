"""Camera discovery + credential self-audit endpoint (gated by API key)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

from argos.discovery import DiscoveredCamera, scan_network

router = APIRouter(tags=["discovery"])


class ScanRequest(BaseModel):
    subnet: str | None = None
    sweep: bool = True
    audit_credentials: bool = True


def _camera_dict(cam: DiscoveredCamera) -> dict:
    return {
        "ip": cam.ip,
        "vendor": cam.vendor,
        "model": cam.model,
        "channels": cam.channels,
        "reachable_http": cam.reachable_http,
        "reachable_rtsp": cam.reachable_rtsp,
        "insecure": cam.insecure,
        "insecure_default_credential": cam.default_credential.masked() if cam.insecure else None,
        "rtsp_urls": cam.rtsp_urls(substream=True),
    }


@router.post("/discovery/scan")
async def discovery_scan(body: ScanRequest) -> list[dict]:
    cameras = await asyncio.to_thread(
        scan_network,
        subnet=body.subnet,
        do_sweep=body.sweep,
        audit_credentials=body.audit_credentials,
    )
    return [_camera_dict(c) for c in cameras]
