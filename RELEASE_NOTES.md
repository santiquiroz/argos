# Argos 0.2.0

A big feature release: real-time monitoring, smart alerting, AI digests, and a full admin UI —
all local, on your own hardware (AMD GPU via ONNX Runtime + DirectML).

## Install (Windows)

1. Run **`ArgosSetup-0.2.0.exe`**.
2. Install ffmpeg (RTSP decode / live view): `winget install Gyan.FFmpeg`.
3. Launch Argos → open the printed URL (`http://localhost:8080`) → paste the API key from the console.

## New in 0.2.0

- **Zones & tripwires** — draw polygons on the live view: *alert* zones fire on entry, *ignore*
  zones mask out noise (a tree, the street) so you get fewer false alerts.
- **Smart notifications** — a generic webhook (ntfy / Home Assistant / Discord / Telegram / Slack)
  with per-event-kind filtering and a cooldown so the same person/camera can't spam you. Editable
  from the UI, with a test button.
- **AI daily digest** — a natural-language summary of the last 24h. Always available deterministically;
  point it at your own local LLM (bipolar-code, Anthropic-compatible) for a polished write-up —
  nothing leaves your network.
- **Person profiles** — click any person for a cross-camera observation timeline with thumbnails;
  enroll (name) them; **merge** split identities.
- **System dashboard** — live VRAM (real DXGI probe), CPU/RAM, uptime, and 24h activity counts.
- **Editable settings** — notifications, retention and the LLM config change live, no `.env` edit.
- **Config backup** — export/import cameras, zones and settings to move between machines.
- **App icon** and favicon.

## Still here from 0.1.0

- Live MJPEG camera grid straight from your HiLook/Hikvision DVR (or Frigate).
- LAN camera **discovery** with default-password **audit**, one-click add.
- Direct-RTSP pipeline (YOLO person detector + tracker) — no Frigate required — or a Frigate consumer.

## Notes

- Higher-order analytics (pose, re-ID, face, action, gait) need model weights — see `docs/models.md`.
- The app stores its data (SQLite DB, crops, `.env`) in `%LOCALAPPDATA%\Argos`.
- Zones currently evaluate on the direct-RTSP path; Frigate-path zones are pending box-format
  verification. This is a **self-audit / own-premises** tool — read `PRIVACY.md`.

## Verified

Packaged binary launches and serves the SPA + API; **59 tests green**; frontend type-checks and
builds; the DXGI VRAM probe reads a real value on an RX 7800 XT.
