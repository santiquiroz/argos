"""Direct RTSP ingest for HiLook/Hikvision DVRs (no Frigate).

Per camera: an ffmpeg raw-``rgb24`` frame source (with ``-rtsp_transport tcp``, reconnect/backoff)
feeds a YOLO person detector + IoU tracker; person crops are emitted as ``PersonObservation``s. Each
camera runs in its own thread and pushes into a bounded newest-wins queue so latency never grows.

Detection is throttled (every Nth frame) to keep GPU load sane across multiple cameras. Point the
cameras at the DVR **sub-streams** (``…02``) — detection is cheap on low-res, and the crop is taken
from the same frame.

See ``docs/frigate-integration.md``.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import threading
import time
from collections.abc import AsyncIterator
from typing import Protocol

import numpy as np

from argos.detect.tracker import IouTracker
from argos.ingest.base import Ingestor, PersonObservation
from argos.logging import get_logger

log = get_logger(__name__)

_RECONNECT_BACKOFF_S = (1.0, 2.0, 5.0, 10.0)
_DETECT_EVERY = 5          # run the detector on 1 of every N frames
_MIN_CROP_PX = 24          # ignore crops smaller than this (too small to analyze)


def _probe_stream_size(url: str) -> tuple[int, int] | None:
    """Return ``(width, height)`` via ffprobe, or ``None`` if unavailable."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return None
    cmd = [
        ffprobe, "-v", "error", "-rtsp_transport", "tcp",
        "-select_streams", "v:0", "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x", url,
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=True).stdout
        w, h = out.strip().split("x")
        return int(w), int(h)
    except (subprocess.SubprocessError, ValueError):
        return None


class FfmpegRtspFrameSource:
    """Decode an RTSP stream to raw RGB frames over an ffmpeg stdout pipe.

    Yields ``(H, W, 3)`` uint8 arrays. Reconnects with backoff on drop. Blocking; run in a thread.
    """

    def __init__(self, url: str, size: tuple[int, int]) -> None:
        self._url = url
        self._width, self._height = size
        self._proc: subprocess.Popen | None = None
        self._stop = False

    def _spawn(self) -> subprocess.Popen:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise RuntimeError("ffmpeg not found on PATH")
        cmd = [
            ffmpeg, "-nostdin", "-loglevel", "error",
            "-rtsp_transport", "tcp", "-i", self._url,
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ]
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def _read_frame(self, proc: subprocess.Popen) -> np.ndarray | None:
        n = self._width * self._height * 3
        buf = proc.stdout.read(n) if proc.stdout else b""
        if len(buf) < n:
            return None
        return np.frombuffer(buf, dtype=np.uint8).reshape(self._height, self._width, 3)

    def frames(self):
        attempt = 0
        while not self._stop:
            self._proc = self._spawn()
            while not self._stop:
                frame = self._read_frame(self._proc)
                if frame is None:
                    break
                yield frame
            self._kill()
            if self._stop:
                break
            backoff = _RECONNECT_BACKOFF_S[min(attempt, len(_RECONNECT_BACKOFF_S) - 1)]
            attempt += 1
            log.warning("rtsp_reconnect", url_tail=self._url[-24:], backoff_s=backoff)
            time.sleep(backoff)

    def _kill(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.kill()
            self._proc.wait(timeout=5)
        self._proc = None

    def stop(self) -> None:
        self._stop = True
        self._kill()


class PersonDetector(Protocol):
    @property
    def available(self) -> bool: ...

    def detect(self, frame: np.ndarray) -> list[tuple[int, int, int, int, float]]:
        ...


def _crop(frame: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray | None:
    x1, y1, x2, y2 = box
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < _MIN_CROP_PX or y2 - y1 < _MIN_CROP_PX:
        return None
    return frame[y1:y2, x1:x2].copy()


class RtspIngestor(Ingestor):
    def __init__(self, cameras: dict[str, str], detector: PersonDetector | None) -> None:
        self._cameras = cameras
        self._detector = detector
        self._sources: list[FfmpegRtspFrameSource] = []
        self._threads: list[threading.Thread] = []
        self._queue: asyncio.Queue[PersonObservation] = asyncio.Queue(maxsize=128)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop = False

    async def observations(self) -> AsyncIterator[PersonObservation]:
        self._require_detector()
        self._loop = asyncio.get_running_loop()
        self._start_camera_threads()
        while not self._stop:
            yield await self._queue.get()

    def _require_detector(self) -> None:
        if self._detector is None or not self._detector.available:
            raise RuntimeError(
                "Direct-RTSP ingest needs a person detector model at "
                "<models_dir>/detector.onnx. Export one with scripts/export_yolo.py, "
                "or use the Frigate ingest path (ARGOS_INGEST=frigate)."
            )

    def _start_camera_threads(self) -> None:
        for name, url in self._cameras.items():
            size = _probe_stream_size(url)
            if size is None:
                log.error("rtsp_probe_failed", camera=name, hint="install ffprobe / check URL+creds")
                continue
            source = FfmpegRtspFrameSource(url, size)
            self._sources.append(source)
            thread = threading.Thread(target=self._run_camera, args=(name, source), daemon=True)
            thread.start()
            self._threads.append(thread)
            log.info("rtsp_camera_started", camera=name, size=f"{size[0]}x{size[1]}")

    def _run_camera(self, name: str, source: FfmpegRtspFrameSource) -> None:
        tracker = IouTracker()
        assert self._detector is not None
        for index, frame in enumerate(source.frames()):
            if self._stop:
                break
            if index % _DETECT_EVERY != 0:
                continue
            detections = self._detector.detect(frame)
            tracks = tracker.update([d[:4] for d in detections])
            for track_id, box in tracks:
                self._emit(name, track_id, box, frame)

    def _emit(self, camera: str, track_id: int, box: tuple[int, int, int, int], frame: np.ndarray) -> None:
        crop = _crop(frame, box)
        if crop is None or self._loop is None:
            return
        obs = PersonObservation(
            camera=camera,
            track_id=f"{camera}:{track_id}",
            crop=crop,
            box=box,
            frame=frame,
        )
        self._loop.call_soon_threadsafe(self._enqueue, obs)

    def _enqueue(self, obs: PersonObservation) -> None:
        if self._queue.full():
            try:
                self._queue.get_nowait()  # newest-wins: drop the oldest
            except asyncio.QueueEmpty:
                pass
        self._queue.put_nowait(obs)

    async def close(self) -> None:
        self._stop = True
        for source in self._sources:
            source.stop()
        await asyncio.sleep(0)
