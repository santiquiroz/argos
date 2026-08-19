"""Daily digest: a natural-language summary of the last 24h of camera events.

Always returns a deterministic summary; if an LLM is configured, it's polished into prose.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from argos.llm import LlmClient, build_digest_prompt, deterministic_digest

router = APIRouter(tags=["digest"])


@router.get("/digest")
async def digest(request: Request) -> dict:
    state = request.app.state
    settings = state.settings
    cutoff = time.time() - 86400
    events = [e for e in state.store.recent_events(500) if e["ts"] >= cutoff]
    text = deterministic_digest(events, state.store.stats())
    source = "deterministic"

    if settings.llm_enabled and settings.llm_base_url:
        client = LlmClient(base_url=settings.llm_base_url, api_key=settings.llm_api_key, model=settings.llm_model)
        polished = await client.complete(build_digest_prompt(text))
        if polished:
            text = polished.strip()
            source = "llm"

    return {"text": text, "source": source, "events_24h": len(events), "generated_at": time.time()}
