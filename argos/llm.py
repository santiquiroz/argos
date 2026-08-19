"""Optional LLM integration (Anthropic Messages-compatible) for digests + narration.

Points at any Anthropic Messages API endpoint — designed for a local host like bipolar-code, so
event data never leaves your network. Everything degrades gracefully: if the LLM is off or
unreachable, callers fall back to the deterministic digest.
"""

from __future__ import annotations

from collections import Counter

import httpx

from argos.logging import get_logger

log = get_logger(__name__)

_ANTHROPIC_VERSION = "2023-06-01"

_KIND_LABEL = {
    "behavior": "behaviour alert",
    "zone": "zone entry",
    "new_person": "new person",
    "recognized": "recognized person",
}


def deterministic_digest(events: list[dict], stats: dict) -> str:
    """A plain-language 24h summary built from the data alone (no LLM). Always available."""
    if not events:
        return "No activity recorded in the last 24 hours."
    by_kind = Counter(e["kind"] for e in events)
    cameras = sorted({e["camera"] for e in events if e.get("camera")})
    parts = [f"{len(events)} events across {len(cameras)} camera(s) in the last 24 hours."]
    for kind, count in by_kind.most_common():
        parts.append(f"{count} {_KIND_LABEL.get(kind, kind)}(s).")
    behaviours = [e for e in events if e["kind"] == "behavior" and e.get("label")]
    if behaviours:
        labels = Counter(f"{e['label']} on {e.get('camera', '?')}" for e in behaviours)
        parts.append("Notable: " + ", ".join(f"{lbl} (x{n})" for lbl, n in labels.most_common(5)) + ".")
    zones = [e for e in events if e["kind"] == "zone" and e.get("label")]
    if zones:
        parts.append(f"{len(zones)} zone entries: " + ", ".join(sorted({e["label"] for e in zones})) + ".")
    parts.append(f"{stats.get('persons', 0)} distinct persons seen ({stats.get('enrolled', 0)} enrolled).")
    return " ".join(parts)


def build_digest_prompt(summary: str) -> str:
    return (
        "You are a calm, factual home-security assistant. Based on the camera-event summary below "
        "from the last 24 hours, write a brief digest (3-4 sentences) for the homeowner. State what "
        "happened plainly and flag anything that looks unusual or worth attention; do not invent "
        "details beyond the summary.\n\nSummary:\n" + summary
    )


class LlmClient:
    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    async def complete(self, prompt: str, *, max_tokens: int = 400) -> str | None:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        body = {"model": self._model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self._base_url}/v1/messages", headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
            return _extract_text(data)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            log.warning("llm_call_failed", error=str(exc))
            return None


def _extract_text(data: dict) -> str | None:
    content = data.get("content")
    if isinstance(content, list) and content and isinstance(content[0], dict):
        return content[0].get("text")
    return None
