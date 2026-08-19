"""Minimal IoU tracker — assigns stable track ids so temporal analyzers can window per person.

Greedy IoU association: each detection is matched to the best-overlapping active track; unmatched
detections start new tracks; tracks unseen for ``max_age`` frames are dropped. Good enough for a few
cameras of pedestrian traffic; swap for ByteTrack if crowds/occlusion demand it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Box = tuple[int, int, int, int]


def iou(a: Box, b: Box) -> float:
    ax1, ay1, ax2, ay2 = a[:4]
    bx1, by1, bx2, by2 = b[:4]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / float(area_a + area_b - inter)


@dataclass
class _Track:
    track_id: int
    box: Box
    age: int = 0


@dataclass
class IouTracker:
    iou_threshold: float = 0.3
    max_age: int = 30
    _tracks: list[_Track] = field(default_factory=list)
    _next_id: int = 1

    def update(self, detections: list[Box]) -> list[tuple[int, Box]]:
        """Associate detections to tracks. Returns ``(track_id, box)`` for matched/new tracks."""
        matched = self._associate(detections)
        self._age_and_prune({t.track_id for _, t in matched})
        return [(track.track_id, box) for box, track in matched]

    def _associate(self, detections: list[Box]) -> list[tuple[Box, _Track]]:
        used: set[int] = set()
        result: list[tuple[Box, _Track]] = []
        for det in detections:
            track = self._best_match(det, used)
            if track is None:
                track = _Track(track_id=self._next_id, box=det)
                self._next_id += 1
                self._tracks.append(track)
            else:
                track.box = det
                track.age = 0
            used.add(track.track_id)
            result.append((det, track))
        return result

    def _best_match(self, det: Box, used: set[int]) -> _Track | None:
        best, best_iou = None, self.iou_threshold
        for track in self._tracks:
            if track.track_id in used:
                continue
            score = iou(det, track.box)
            if score >= best_iou:
                best, best_iou = track, score
        return best

    def _age_and_prune(self, matched_ids: set[int]) -> None:
        for track in self._tracks:
            if track.track_id not in matched_ids:
                track.age += 1
        self._tracks = [t for t in self._tracks if t.age <= self.max_age]
