"""Runtime configuration. Reads env vars (prefix ``ARGOS_``) and an optional ``.env`` file.

Pattern mirrors bipolar-code's ``core/config.py``: pydantic-settings + a cached accessor.
"""

from __future__ import annotations

import os
import secrets
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_base() -> Path:
    """Writable base dir. Under a PyInstaller build, Program Files isn't writable — use LOCALAPPDATA."""
    if getattr(sys, "frozen", False):
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(root) / "Argos"
    return Path(".")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ARGOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    api_key: str = ""
    cors_origins: str = "http://localhost:5173"

    # Storage
    data_dir: Path = Field(default_factory=lambda: _default_base() / "data")
    models_dir: Path = Field(default_factory=lambda: _default_base() / "models" / "weights")

    # Inference
    device: str = "dml:0"  # "dml:N" | "cpu"
    prefer_fp16: bool = True
    min_free_vram_mb: int = 768
    gpu_concurrency: int = 2

    # Ingest
    ingest: str = "frigate"  # "frigate" | "rtsp"
    frigate_url: str = "http://frigate.lan:5000"
    mqtt_host: str = "frigate.lan"
    mqtt_port: int = 1883
    mqtt_user: str | None = None
    mqtt_password: str | None = None
    rtsp_cameras: str = ""  # "name=url;name=url"

    # Analyzers
    enable_pose: bool = True
    enable_action: bool = True
    enable_face: bool = True
    enable_reid: bool = True
    enable_gait: bool = False

    # Retention (days)
    retain_crops_days: int = 14
    retain_embeddings_days: int = 30
    retain_events_days: int = 90

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def rtsp_camera_map(self) -> dict[str, str]:
        """Parse ``name=url;name=url`` into a dict. Malformed pairs are skipped."""
        result: dict[str, str] = {}
        for pair in self.rtsp_cameras.split(";"):
            pair = pair.strip()
            if "=" not in pair:
                continue
            name, url = pair.split("=", 1)
            if name.strip() and url.strip():
                result[name.strip()] = url.strip()
        return result

    def db_path(self) -> Path:
        return self.data_dir / "argos.db"

    def crops_dir(self) -> Path:
        return self.data_dir / "crops"


def _ensure_api_key(settings: Settings) -> Settings:
    """Generate and persist an API key on first run if none was provided."""
    if settings.api_key:
        return settings
    settings.api_key = secrets.token_urlsafe(32)
    return settings


def _ensure_dirs(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    settings.crops_dir().mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = _ensure_api_key(Settings())
    _ensure_dirs(settings)
    return settings
