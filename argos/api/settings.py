"""Read-only settings snapshot for the UI (no secrets)."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["settings"])


@router.get("/settings")
def get_settings_snapshot(request: Request) -> dict:
    s = request.app.state.settings
    return {
        "device": s.device,
        "ingest": s.ingest,
        "prefer_fp16": s.prefer_fp16,
        "frigate_url": s.frigate_url,
        "analyzers": {
            "pose": s.enable_pose,
            "action": s.enable_action,
            "face": s.enable_face,
            "reid": s.enable_reid,
            "gait": s.enable_gait,
        },
        "retention_days": {
            "crops": s.retain_crops_days,
            "embeddings": s.retain_embeddings_days,
            "events": s.retain_events_days,
        },
        "notifications": {
            "enabled": bool(s.notify_webhook_url),
            "notify_on": s.notify_on,
            "cooldown_s": s.notify_cooldown_s,
        },
    }
