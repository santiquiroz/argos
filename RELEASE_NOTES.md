# Argos 0.1.0

First packaged release: a local-first behavioural & identity analytics layer for your own security
cameras, with a full admin UI and real-time live view. Runs 100% on your hardware (AMD GPU via
ONNX Runtime + DirectML), nothing leaves your network.

## Install (Windows)

1. Run **`ArgosSetup-0.1.0.exe`**.
2. Install ffmpeg (RTSP decode / live view): `winget install Gyan.FFmpeg`.
3. Launch Argos → open the printed URL (`http://localhost:8080`) → paste the API key from the console.

## What's in it

- **Live cameras** — real-time MJPEG grid straight from your HiLook/Hikvision DVR (or Frigate).
- **Discovery** — scan your LAN for cameras and **audit default passwords**, add cameras in one click.
- **Direct-RTSP pipeline** — YOLO person detector + tracker, no Frigate required (export a model with
  `scripts/export_yolo.py`), or consume a Frigate NVR over MQTT.
- **Persons & events** — anonymous person clusters you can enrol/name, live behaviour/identity event
  feed (SSE).
- **SURU-aligned UI** — Flat design, Space Grotesk / DM Sans, light + dark, built to drop into the
  SURU web apps.

## Notes

- Higher-order analytics (pose, re-ID, face, action, gait) need model weights — see
  `docs/models.md` / `scripts/download_models.py`. Each model carries its own license.
- The app writes its data (SQLite DB, crops, `.env`) to `%LOCALAPPDATA%\Argos`.
- This is a **self-audit / own-premises** tool — read `PRIVACY.md` before deploying.

## Verified

Packaged binary launches, serves the SPA + API (health 200), frozen-aware data dir works; 35 tests
green; frontend type-checks and builds.
