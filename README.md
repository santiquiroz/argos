# Argos

**Local-first behavioral & identity analytics layer for your own security cameras.**

Argos is the layer that sits *on top of* your camera stack (a [Frigate](https://frigate.video)
NVR, or a Hikvision/HiLook DVR directly over RTSP) and runs the higher-order computer-vision
models that raw NVRs don't: **pose estimation, skeleton-based action / behaviour recognition,
cross-camera person re-identification, face embeddings, and (experimental) gait recognition.**

It turns "a camera saw a person" into "*this* person walked through the yard at 03:14, the same
person the porch camera saw yesterday, and they were loitering." All of it runs **100% on your
own hardware** — no cloud, no third-party API, no footage leaving your network.

Argos is built to run its inference on an **AMD GPU via ONNX Runtime + DirectML** (no CUDA, no
ROCm), reusing the inference core proven in [Upflow](https://github.com/santiquiroz). It exposes a
[bipolar-code](https://github.com/santiquiroz)-style FastAPI + React web UI.

> ⚠️ **Read [PRIVACY.md](PRIVACY.md) before you deploy this.** Face recognition, gait recognition
> and person profiling are powerful and legally regulated in many places. Argos is designed for
> monitoring **premises you own or are authorised to monitor**. You are responsible for lawful use.

---

## Why not just use Frigate?

You should use Frigate — Argos is designed to *complement* it, not replace it. Frigate (0.16+) is
excellent at the substrate: RTSP ingest, motion, object detection, tracking, recording, plus
built-in face recognition, license-plate recognition and CLIP semantic search. Argos consumes
Frigate's tracked-object events and adds the analytics Frigate does **not** do:

| Capability | Frigate | Argos |
|---|:---:|:---:|
| RTSP ingest / recording / object detection / tracking | ✅ | consumes it |
| Face recognition | ✅ (0.16+) | ✅ (own embedding store, fused with re-ID + gait) |
| License-plate recognition | ✅ | — |
| Semantic search (CLIP) | ✅ (0.17+) | — |
| Pose estimation | — | ✅ |
| **Action / behaviour recognition** (loiter, fall, run, climb, fight) | — | ✅ |
| **Cross-camera person re-identification** | — | ✅ |
| **Gait recognition** | — | ✅ (experimental) |
| **Unified person profiles** (timeline + enroll + merge) | — | ✅ |
| **Zones / tripwires** (alert + ignore-mask) | ✅ | ✅ (editable in-UI) |
| **Smart notifications** (webhook, filtered + cooldown) | via HA | ✅ built-in |
| **AI daily digest** (local-LLM, private) | — | ✅ |
| **System dashboard** (real VRAM/CPU/uptime) | — | ✅ |

If you don't run Frigate, Argos can pull RTSP directly from a Hikvision/HiLook DVR and run its own
person detector — see [`docs/frigate-integration.md`](docs/frigate-integration.md) for both paths.

---

## Architecture at a glance

```
 IP cameras / HiLook DVR
        │ RTSP
        ▼
┌───────────────────┐        ┌──────────────────────────────────────────────┐
│  Ingest adapter   │        │              Argos analysis core               │
│  ┌─────────────┐  │        │                                                │
│  │ Frigate MQTT│──┼──crops─▶│  pose → action ┐                              │
│  │  + snapshots│  │        │  face embed    ├─▶ identity fusion ─▶ profiles │
│  └─────────────┘  │        │  re-ID embed   ┘        │                      │
│  ┌─────────────┐  │        │  gait (silhouette, exp.)│                      │
│  │ Direct RTSP │──┼──frames▶│                         ▼                      │
│  │ (+ detector)│  │        │              SQLite + vector index            │
│  └─────────────┘  │        └──────────────────────────────────────────────┘
└───────────────────┘                          │
        ONNX Runtime + DirectML (AMD GPU)       ▼
                                         FastAPI  ◀── React/Vite UI + SSE live events
```

Full design and the decisions behind it: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Status

**v0.2.0 — working alpha, packaged.** Full admin UI (live cameras, discovery, zones, persons,
events, settings), direct-RTSP detection pipeline, notifications, AI digest, system dashboard, and a
Windows installer. Analyzer model weights (pose / re-ID / face / action / gait) are **not** bundled —
see [`docs/models.md`](docs/models.md) and `scripts/download_models.py`; person **detection** on the
direct path uses a YOLO model you export with `scripts/export_yolo.py`. Grab the installer from
[Releases](https://github.com/santiquiroz/argos/releases). See [ROADMAP.md](ROADMAP.md) for what's
next.

---

## Quick start (dev)

```bash
# backend
cd argos
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev]"
cp .env.example .env                                # then edit
python -m argos                                     # http://localhost:8080

# frontend (optional, for the UI)
cd frontend
npm install
npm run dev                                          # http://localhost:5173
```

Run the tests:

```bash
pytest
```

Download analyzer models (interactive, opt-in per model):

```bash
python scripts/download_models.py --list
python scripts/download_models.py pose face
```

---

## Run it with your HiLook DVR (direct path, no Frigate)

```bash
# 0. install ffmpeg (RTSP decode) and the deps
winget install Gyan.FFmpeg              # Windows
pip install -e ".[dev,directml]"

# 1. discover cameras on your LAN + audit default passwords → get RTSP URLs
python scripts/discover_cameras.py
#    (or test one stream directly:)
python scripts/test_camera.py "rtsp://admin:PASS@192.168.1.10:554/Streaming/Channels/102"

# 2. export a person detector to ONNX (one-time)
pip install ultralytics
python scripts/export_yolo.py           # → models/weights/detector.onnx

# 3. point Argos at the DVR and run
#    in .env:
#      ARGOS_INGEST=rtsp
#      ARGOS_RTSP_CAMERAS=front=rtsp://admin:PASS@192.168.1.10:554/Streaming/Channels/102
python -m argos                         # http://localhost:8080  (dashboard shows live person events)
```

Downloading the pose/re-ID/face models (`python scripts/download_models.py`) lights up the
higher-order analytics (identity, behaviour) on top of person detection.

## Requirements

- **Windows 11** with an **AMD GPU** (RX 7800 XT class or better) for the DirectML inference path.
  CPU fallback works everywhere but is slow.
- **Python 3.12+**
- **ffmpeg** on `PATH` (RTSP decoding).
- Optional: a running **Frigate** instance + **MQTT broker** (recommended ingest path).

---

## License

[AGPL-3.0-or-later](LICENSE). Model weights downloaded via `scripts/download_models.py` carry their
**own** licenses (some are research/non-commercial only) — see [`docs/models.md`](docs/models.md).
Argos does not redistribute them.
