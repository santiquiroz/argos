"""Frigate consumer ingest (recommended path).

Subscribes to Frigate's ``frigate/events`` MQTT topic, filters ``person`` tracked objects, and
fetches the best snapshot per event from Frigate's HTTP API. Frigate has already done decode,
motion, tracking and best-frame selection, so Argos spends GPU only on analytics.

See ``docs/frigate-integration.md``.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import cv2
import httpx
import numpy as np
import paho.mqtt.client as mqtt

from argos.config import Settings
from argos.ingest.base import Ingestor, PersonObservation
from argos.logging import get_logger

log = get_logger(__name__)

_EVENTS_TOPIC = "frigate/events"


def _extract_person_event(payload: bytes) -> dict | None:
    """Return ``{id, camera, box}`` for a live ``person`` event, else ``None``."""
    try:
        msg = json.loads(payload)
    except (ValueError, TypeError):
        return None
    if msg.get("type") == "end":
        return None
    after = msg.get("after") or {}
    if after.get("label") != "person":
        return None
    event_id = after.get("id")
    if not event_id:
        return None
    return {"id": event_id, "camera": after.get("camera", "unknown"), "box": after.get("box")}


def _decode_jpeg_rgb(data: bytes) -> np.ndarray | None:
    buf = np.frombuffer(data, dtype=np.uint8)
    bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if bgr is None:
        return None
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


class FrigateIngestor(Ingestor):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=256)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._http = httpx.AsyncClient(timeout=5.0)
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if settings.mqtt_user:
            self._client.username_pw_set(settings.mqtt_user, settings.mqtt_password or "")
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def _on_connect(self, client: mqtt.Client, *_: object) -> None:
        client.subscribe(_EVENTS_TOPIC)
        log.info("frigate_mqtt_connected", topic=_EVENTS_TOPIC)

    def _on_message(self, _client: object, _userdata: object, message: mqtt.MQTTMessage) -> None:
        event = _extract_person_event(message.payload)
        if event is None or self._loop is None:
            return
        # paho runs this on its own thread; hop back to the event loop.
        self._loop.call_soon_threadsafe(self._enqueue, event)

    def _enqueue(self, event: dict) -> None:
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("frigate_queue_full_dropping", event_id=event.get("id"))

    async def _fetch_snapshot(self, event_id: str) -> np.ndarray | None:
        url = f"{self._settings.frigate_url}/api/events/{event_id}/snapshot.jpg"
        try:
            resp = await self._http.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("frigate_snapshot_failed", event_id=event_id, error=str(exc))
            return None
        return _decode_jpeg_rgb(resp.content)

    async def observations(self) -> AsyncIterator[PersonObservation]:
        self._loop = asyncio.get_running_loop()
        self._client.connect_async(self._settings.mqtt_host, self._settings.mqtt_port)
        self._client.loop_start()
        while True:
            event = await self._queue.get()
            crop = await self._fetch_snapshot(event["id"])
            if crop is None:
                continue
            box = tuple(event["box"]) if event.get("box") else None
            yield PersonObservation(
                camera=event["camera"],
                track_id=event["id"],
                crop=crop,
                box=box,
            )

    async def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
        await self._http.aclose()
