"""Send a test notification so users can verify their webhook wiring."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["notify"])


@router.post("/notify/test")
async def notify_test(request: Request) -> dict:
    notifier = request.app.state.notifier
    if not notifier.enabled:
        raise HTTPException(status_code=400, detail="no ARGOS_NOTIFY_WEBHOOK_URL configured")
    event = {"id": f"test-{int(time.time())}", "kind": "behavior", "label": "test alert", "camera": "test", "score": 1.0, "ts": time.time()}
    await notifier._post(event)  # bypass the policy for an explicit test
    return {"sent": True}
