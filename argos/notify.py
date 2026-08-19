"""Event notifications with filtering + cooldown (the #1 self-hosted-NVR pain: alert fatigue).

A generic JSON webhook covers ntfy, Home Assistant, Discord, Telegram-bot, Slack, n8n, etc. The
policy decides *whether* to notify (which event kinds, and a per-subject cooldown so the same person
or camera doesn't spam you), and is pure/testable. Delivery is fire-and-forget so a slow receiver
never stalls the pipeline.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from argos.logging import get_logger

log = get_logger(__name__)


def parse_kinds(value: str) -> set[str]:
    return {k.strip() for k in value.split(",") if k.strip()}


class NotificationPolicy:
    """Decides whether an event should notify. Pure: no I/O.

    ``notify_on`` limits which event kinds fire. ``cooldown_s`` suppresses repeats for the same
    subject (person or camera) within the window, so a lingering person doesn't spam alerts.
    """

    def __init__(self, notify_on: set[str], cooldown_s: float) -> None:
        self._notify_on = notify_on
        self._cooldown_s = cooldown_s
        self._last_sent: dict[tuple[str, str], float] = {}

    @staticmethod
    def subject(event: dict) -> str:
        return event.get("person_id") or event.get("camera") or event.get("id") or "?"

    def should_notify(self, event: dict, now: float) -> bool:
        kind = event.get("kind", "")
        if kind not in self._notify_on:
            return False
        key = (kind, self.subject(event))
        last = self._last_sent.get(key)
        if last is not None and now - last < self._cooldown_s:
            return False
        self._last_sent[key] = now
        return True


def format_message(event: dict) -> tuple[str, str]:
    """(title, body) for an event."""
    kind = event.get("kind")
    camera = event.get("camera") or "a camera"
    if kind == "behavior":
        pct = int((event.get("score") or 0) * 100)
        return (f"Argos: {event.get('label', 'behaviour')} detected", f"{event.get('label')} ({pct}%) on {camera}")
    if kind == "zone":
        return (f"Argos: zone entry — {event.get('label')}", f"Someone entered '{event.get('label')}' on {camera}")
    if kind == "new_person":
        return ("Argos: new person", f"A new person was seen on {camera}")
    if kind == "recognized":
        return ("Argos: recognized person", f"A known person was seen on {camera}")
    return ("Argos event", f"{kind} on {camera}")


class Notifier:
    def __init__(self, *, webhook_url: str, policy: NotificationPolicy) -> None:
        self._url = webhook_url
        self._policy = policy
        self._client = httpx.AsyncClient(timeout=5.0)

    @property
    def enabled(self) -> bool:
        return bool(self._url)

    def dispatch(self, event: dict) -> None:
        """Non-blocking: schedule a POST if the policy allows it."""
        if not self.enabled or not self._policy.should_notify(event, time.time()):
            return
        asyncio.create_task(self._post(event))

    async def _post(self, event: dict) -> None:
        title, body = format_message(event)
        payload = {"title": title, "message": body, "event": event}
        try:
            # ntfy also reads the Title header + plain body; JSON works for Discord/HA/n8n/Slack.
            await self._client.post(self._url, json=payload, headers={"Title": title})
            log.info("notify_sent", kind=event.get("kind"), subject=NotificationPolicy.subject(event))
        except httpx.HTTPError as exc:
            log.warning("notify_failed", error=str(exc))

    async def close(self) -> None:
        await self._client.aclose()


def build_notifier(webhook_url: str, notify_on: str, cooldown_s: float) -> Notifier:
    policy = NotificationPolicy(parse_kinds(notify_on), cooldown_s)
    return Notifier(webhook_url=webhook_url, policy=policy)
