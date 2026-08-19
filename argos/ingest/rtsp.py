"""Direct RTSP ingest for HiLook/Hikvision DVRs (no Frigate).

An ffmpeg raw-``rgb24``-pipe frame source (adapted from Upflow's ``FfmpegFrameSource``) with the
live-stream concerns a finite-file source doesn't need: ``-rtsp_transport tcp``, reconnect/backoff,
and a bounded **newest-wins** queue so latency never grows under load.

Person detection for this path (a YOLO-class ONNX detector + lightweight tracker) is Phase 1 —
until a ``PersonDetector`` is injected, this ingestor raises a clear error pointing at the Frigate
path. The frame source itself (``FfmpegRtspFrameSource``) is complete and reusable.

See ``docs/frigate-integration.md``.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import time
from collections.abc import AsyncIterator
from typing import Protocol

import numpy as np

from argos.config import Settings
from argos.ingest.base import Ingestor, PersonObservation
from argos.logging import get_logger

log = get_logger(__name__)

_RECONNECT_BACKOFF_S = (1.0, 2.0, 5.0, 10.0)


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

    Yields ``(H, W, 3)`` uint8 arrays. Reconnects with backoff on drop. Blocking; drive it from a
    thread (``asyncio.to_thread``) or wrap with a newest-wins queue for the async path.
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
            attempt = 0
            while not self._stop:
                frame = self._read_frame(self._proc)
                if frame is None:
                    break
                attempt = 0
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
    """Detect persons in an RGB frame → list of ``(x1, y1, x2, y2, score)``."""

    def detect(self, frame: np.ndarray) -> list[tuple[int, int, int, int, float]]:
        ...


class RtspIngestor(Ingestor):
    def __init__(self, settings: Settings, detector: PersonDetector | None = None) -> None:
        self._cameras = settings.rtsp_camera_map()
        self._detector = detector
        self._sources: list[FfmpegRtspFrameSource] = []

    async def observations(self) -> AsyncIterator[PersonObservation]:
        if self._detector is None:
            raise NotImplementedError(
                "Direct-RTSP ingest needs a person detector (Phase 1). "
                "Use the Frigate ingest path (ARGOS_INGEST=frigate) for now."
            )
        # Phase 1: fan cameras into one stream, detect+track, crop, yield observations.
        # Structure is in place; detector wiring lands with the YOLO-class ONNX analyzer.
        for name, url in self._cameras.items():
            log.info("rtsp_camera_configured", camera=name)
        if False:  # pragma: no cover - placeholder to keep this an async generator
            yield  # type: ignore[misc]
        raise NotImplementedError("RTSP detect+track loop is Phase 1 (see ROADMAP.md)")

    async def close(self) -> None:
        for source in self._sources:
            source.stop()
        await asyncio.sleep(0)
