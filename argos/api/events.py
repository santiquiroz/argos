"""Event history + live SSE stream."""

from __future__ import annotations

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(tags=["events"])


@router.get("/events")
def recent_events(request: Request, limit: int = 100) -> list[dict]:
    return request.app.state.store.recent_events(limit=min(limit, 500))


@router.get("/events/stream")
async def stream_events(request: Request) -> EventSourceResponse:
    bus = request.app.state.bus

    async def event_generator():
        async for event in bus.subscribe():
            if await request.is_disconnected():
                break
            yield {"event": event["kind"], "data": event}

    return EventSourceResponse(event_generator())
