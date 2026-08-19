#!/usr/bin/env python3
"""Test connectivity to a HiLook/Hikvision DVR RTSP stream - no models needed.

Confirms your URL, credentials, network and ffmpeg decode work *before* wiring up the full
pipeline. Probes the stream size, grabs a few frames, and saves the first one as a JPEG.

Usage:
    python scripts/test_camera.py "rtsp://user:pass@dvr.lan:554/Streaming/Channels/102"
    python scripts/test_camera.py --from-env            # use the first ARGOS_RTSP_CAMERAS entry
    python scripts/test_camera.py <url> --frames 30 --size 1920x1080 --out snap.jpg

Requires ffmpeg + ffprobe on PATH and: pip install opencv-python-headless numpy
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

# Allow running from a source checkout without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from argos.ingest.rtsp import FfmpegRtspFrameSource, _probe_stream_size  # noqa: E402


def _redact(url: str) -> str:
    """Hide credentials when printing a URL."""
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        return f"{scheme}://***@{rest.split('@', 1)[1]}"
    return url


def _first_env_camera() -> str | None:
    from argos.config import get_settings

    cameras = get_settings().rtsp_camera_map()
    if not cameras:
        return None
    name, url = next(iter(cameras.items()))
    print(f"Using camera '{name}' from ARGOS_RTSP_CAMERAS")
    return url


def _parse_size(text: str | None) -> tuple[int, int] | None:
    if not text:
        return None
    w, h = text.lower().split("x")
    return int(w), int(h)


def run(url: str, *, frames: int, size: tuple[int, int] | None, out: Path) -> int:
    print(f"Camera: {_redact(url)}")

    resolved = size or _probe_stream_size(url)
    if resolved is None:
        print("FAIL: could not probe stream size (ffprobe missing, or URL/credentials wrong, or "
              "camera unreachable). Pass --size WxH to skip probing.", file=sys.stderr)
        return 1
    print(f"Resolved stream size: {resolved[0]}x{resolved[1]}")

    source = FfmpegRtspFrameSource(url, resolved)
    grabbed = 0
    first = None
    start = time.time()
    try:
        for frame in source.frames():
            if first is None:
                first = frame
            grabbed += 1
            if grabbed >= frames:
                break
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        source.stop()

    elapsed = max(time.time() - start, 1e-6)
    if first is None:
        print("FAIL: connected but decoded 0 frames.", file=sys.stderr)
        return 1

    cv2.imwrite(str(out), cv2.cvtColor(first, cv2.COLOR_RGB2BGR))
    print(f"OK: decoded {grabbed} frames in {elapsed:.1f}s (~{grabbed / elapsed:.1f} fps).")
    print(f"Saved first frame to {out.resolve()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", nargs="?", help="RTSP URL of a DVR channel")
    parser.add_argument("--from-env", action="store_true", help="use first ARGOS_RTSP_CAMERAS entry")
    parser.add_argument("--frames", type=int, default=15, help="frames to grab (default 15)")
    parser.add_argument("--size", help="WxH, skip ffprobe (e.g. 1920x1080)")
    parser.add_argument("--out", type=Path, default=Path("camera-test.jpg"))
    args = parser.parse_args()

    url = args.url or (_first_env_camera() if args.from_env else None)
    if not url:
        parser.error("provide an RTSP URL or use --from-env with ARGOS_RTSP_CAMERAS set")
    return run(url, frames=args.frames, size=_parse_size(args.size), out=args.out)


if __name__ == "__main__":
    raise SystemExit(main())
