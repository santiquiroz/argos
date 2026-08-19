"""Camera CRUD + real-time MJPEG live view.

The MJPEG endpoint transcodes an RTSP stream to a multipart JPEG stream an ``<img>`` can render
directly — no browser plugins, no extra restream server. Authenticated via ``?key=`` because
``<img>`` cannot send headers (see middleware).
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from argos.cameras import Camera
from argos.logging import get_logger

log = get_logger(__name__)
router = APIRouter(tags=["cameras"])

_BOUNDARY = "frame"
_SOI = b"\xff\xd8"
_EOI = b"\xff\xd9"


class CameraCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    url: str = Field(min_length=8)
    enabled: bool = True


@router.get("/cameras")
def list_cameras(request: Request) -> list[dict]:
    return [c.masked() for c in request.app.state.cameras.list()]


@router.post("/cameras")
def add_camera(body: CameraCreate, request: Request) -> dict:
    camera = Camera(name=body.name, url=body.url, enabled=body.enabled)
    request.app.state.cameras.add(camera)
    return camera.masked()


@router.delete("/cameras/{name}")
def remove_camera(name: str, request: Request) -> dict:
    if not request.app.state.cameras.remove(name):
        raise HTTPException(status_code=404, detail="camera not found")
    return {"removed": name}


def _mjpeg_stream(url: str) -> Iterator[bytes]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise HTTPException(status_code=503, detail="ffmpeg not found on PATH")
    cmd = [
        ffmpeg, "-nostdin", "-loglevel", "error", "-rtsp_transport", "tcp", "-i", url,
        "-f", "mjpeg", "-q:v", "7", "-r", "8", "-an", "pipe:1",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        yield from _split_jpegs(proc)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def _split_jpegs(proc: subprocess.Popen) -> Iterator[bytes]:
    buffer = b""
    while True:
        chunk = proc.stdout.read(8192) if proc.stdout else b""
        if not chunk:
            break
        buffer += chunk
        while True:
            start = buffer.find(_SOI)
            end = buffer.find(_EOI, start + 2)
            if start == -1 or end == -1:
                break
            jpeg = buffer[start:end + 2]
            buffer = buffer[end + 2:]
            yield (
                f"--{_BOUNDARY}\r\nContent-Type: image/jpeg\r\n"
                f"Content-Length: {len(jpeg)}\r\n\r\n"
            ).encode() + jpeg + b"\r\n"


@router.get("/cameras/{name}/stream.mjpeg")
def stream_camera(name: str, request: Request) -> StreamingResponse:
    url = request.app.state.cameras.url_for(name)
    if url is None:
        raise HTTPException(status_code=404, detail="camera not found or disabled")
    return StreamingResponse(
        _mjpeg_stream(url),
        media_type=f"multipart/x-mixed-replace; boundary={_BOUNDARY}",
    )
