"""Camera configuration store (JSON), so the UI can manage cameras, not just ``.env``.

Seeded once from ``ARGOS_RTSP_CAMERAS`` if the file doesn't exist yet. Credentials live here in
plaintext (same trust level as ``.env``); API responses mask them.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from argos.config import Settings
from argos.logging import get_logger

log = get_logger(__name__)

_CRED_RE = re.compile(r"//([^:/@]+):([^@/]+)@")


def mask_rtsp(url: str) -> str:
    """Hide the password in an RTSP URL for display."""
    return _CRED_RE.sub(lambda m: f"//{m.group(1)}:****@", url)


@dataclass(frozen=True, slots=True)
class Camera:
    name: str
    url: str
    enabled: bool = True

    def masked(self) -> dict:
        return {"name": self.name, "url": mask_rtsp(self.url), "enabled": self.enabled}


class CameraStore:
    def __init__(self, path: Path, seed: dict[str, str] | None = None) -> None:
        self._path = path
        self._lock = threading.Lock()
        if not path.exists() and seed:
            self._write([Camera(name=n, url=u) for n, u in seed.items()])

    def _read(self) -> list[Camera]:
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return [Camera(**item) for item in data]

    def _write(self, cameras: list[Camera]) -> None:
        self._path.write_text(json.dumps([asdict(c) for c in cameras], indent=2), encoding="utf-8")

    def list(self) -> list[Camera]:
        with self._lock:
            return self._read()

    def get(self, name: str) -> Camera | None:
        return next((c for c in self.list() if c.name == name), None)

    def url_for(self, name: str) -> str | None:
        cam = self.get(name)
        return cam.url if cam and cam.enabled else None

    def add(self, camera: Camera) -> None:
        with self._lock:
            cameras = [c for c in self._read() if c.name != camera.name]
            cameras.append(camera)
            self._write(cameras)
        log.info("camera_added", name=camera.name)

    def remove(self, name: str) -> bool:
        with self._lock:
            cameras = self._read()
            remaining = [c for c in cameras if c.name != name]
            if len(remaining) == len(cameras):
                return False
            self._write(remaining)
        log.info("camera_removed", name=name)
        return True


def build_camera_store(settings: Settings) -> CameraStore:
    return CameraStore(settings.data_dir / "cameras.json", seed=settings.rtsp_camera_map())
