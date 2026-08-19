"""Persisted, UI-editable settings overrides layered on top of the ``.env``/env defaults.

Only a safe, hot-applicable subset is editable at runtime (notifications + retention). Device/ingest/
analyzer toggles still come from ``.env`` and need a restart — those aren't exposed here.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from argos.config import Settings
from argos.logging import get_logger

log = get_logger(__name__)

EDITABLE_FIELDS = (
    "notify_webhook_url",
    "notify_on",
    "notify_cooldown_s",
    "retain_crops_days",
    "retain_embeddings_days",
    "retain_events_days",
    "llm_enabled",
    "llm_base_url",
    "llm_api_key",
    "llm_model",
)


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    def read(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}

    def update(self, changes: dict) -> dict:
        with self._lock:
            current = self.read()
            for key, value in changes.items():
                if key in EDITABLE_FIELDS and value is not None:
                    current[key] = value
            self._path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        return current


def apply_overrides(settings: Settings, overrides: dict) -> None:
    """Set editable attributes on the live settings object (mutates in place)."""
    for key, value in overrides.items():
        if key in EDITABLE_FIELDS and hasattr(settings, key):
            setattr(settings, key, value)


def build_settings_store(settings: Settings) -> SettingsStore:
    store = SettingsStore(settings.data_dir / "settings_override.json")
    apply_overrides(settings, store.read())  # apply persisted overrides at startup
    return store
