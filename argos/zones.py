"""Per-camera zones (polygons) in normalized 0..1 coords, so they're resolution-independent.

Two kinds, both aimed at the #1 self-hosted-NVR pain (alert fatigue):
- ``alert``  → a tripwire: entering it emits a "zone" event (and a notification).
- ``ignore`` → a noise mask: detections whose foot point falls inside are suppressed (a tree, the
  street, a flag) so they never create events.

Geometry helpers are pure and unit-tested; storage is a JSON file like the camera store.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

Point = tuple[float, float]


def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    """Ray-casting test. Polygon is a list of (x, y); at least 3 points."""
    if len(polygon) < 3:
        return False
    x, y = point
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi)
        if intersects:
            inside = not inside
        j = i
    return inside


def foot_point_normalized(box: tuple[int, int, int, int], frame_size: tuple[int, int]) -> Point:
    """Bottom-center of a box (where a person stands) in normalized 0..1 coords."""
    x1, y1, x2, y2 = box
    w, h = frame_size
    return ((x1 + x2) / 2.0 / max(w, 1), y2 / max(h, 1))


@dataclass(slots=True)
class Zone:
    camera: str
    name: str
    points: list[Point]
    kind: str = "alert"  # "alert" | "ignore"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def contains(self, point: Point) -> bool:
        return point_in_polygon(point, [tuple(p) for p in self.points])


class ZoneStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    def _read(self) -> list[Zone]:
        if not self._path.exists():
            return []
        return [Zone(**item) for item in json.loads(self._path.read_text(encoding="utf-8"))]

    def _write(self, zones: list[Zone]) -> None:
        self._path.write_text(json.dumps([asdict(z) for z in zones], indent=2), encoding="utf-8")

    def list(self) -> list[Zone]:
        with self._lock:
            return self._read()

    def for_camera(self, camera: str) -> list[Zone]:
        return [z for z in self.list() if z.camera == camera]

    def add(self, zone: Zone) -> Zone:
        with self._lock:
            zones = self._read()
            zones.append(zone)
            self._write(zones)
        return zone

    def remove(self, zone_id: str) -> bool:
        with self._lock:
            zones = self._read()
            remaining = [z for z in zones if z.id != zone_id]
            if len(remaining) == len(zones):
                return False
            self._write(remaining)
        return True


def build_zone_store(data_dir: Path) -> ZoneStore:
    return ZoneStore(data_dir / "zones.json")
