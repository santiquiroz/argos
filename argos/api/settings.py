"""Settings snapshot (no secrets) + hot-editable subset (notifications, retention)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from argos.notify import build_notifier
from argos.settings_store import apply_overrides

router = APIRouter(tags=["settings"])


class SettingsUpdate(BaseModel):
    notify_webhook_url: str | None = None
    notify_on: str | None = None
    notify_cooldown_s: int | None = None
    retain_crops_days: int | None = None
    retain_embeddings_days: int | None = None
    retain_events_days: int | None = None


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
            "webhook_url": s.notify_webhook_url,
            "notify_on": s.notify_on,
            "cooldown_s": s.notify_cooldown_s,
        },
    }


@router.patch("/settings")
async def update_settings(body: SettingsUpdate, request: Request) -> dict:
    state = request.app.state
    changes = body.model_dump(exclude_none=True)
    state.settings_store.update(changes)
    apply_overrides(state.settings, changes)
    if any(k.startswith("notify_") for k in changes):
        notifier = build_notifier(
            state.settings.notify_webhook_url, state.settings.notify_on, state.settings.notify_cooldown_s
        )
        await state.pipeline.set_notifier(notifier)
        state.notifier = notifier
    return get_settings_snapshot(request)
