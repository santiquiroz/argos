"""In-process pub/sub bus for live events (consumed by the SSE endpoint)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class EventBus:
    def __init__(self, maxsize: int = 256) -> None:
        self._subscribers: set[asyncio.Queue[dict]] = set()
        self._maxsize = maxsize

    def publish(self, event: dict) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # a slow subscriber drops events rather than blocking the pipeline

    async def subscribe(self) -> AsyncIterator[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=self._maxsize)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)
