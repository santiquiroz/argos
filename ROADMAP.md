# Roadmap

Legend: ✅ implemented · 🟡 scaffolded (interface + wiring, model/impl pending) · ⏳ planned

## Phase 0 — Foundations
- ✅ Repo, license (AGPL-3.0), architecture doc, privacy statement
- ✅ `pyproject`, config (pydantic-settings), structured logging (structlog)
- ✅ ONNX Runtime + DirectML session factory (ported from Upflow, AMD-only subset)
- ✅ Silent CPU-fallback detection surfaced per model
- 🟡 VRAM admission control (DXGI probe) — port from Upflow `device_semaphores`/`resource_probes`

## Phase 1 — Ingest
- ✅ `PersonObservation` dataclasses + `Ingestor` interface
- ✅ `FrigateIngestor` — MQTT `frigate/events` consumer + snapshot fetch
- ✅ `RtspIngestor` — ffmpeg raw-pipe RTSP source with reconnect/backoff/frame-drop, per-camera threads
- ✅ Built-in YOLO person detector (ONNX) for the direct-RTSP path + `scripts/export_yolo.py`
- ✅ Lightweight IoU tracker for stable per-camera track ids

## Phase 1.5 — Onboarding / discovery
- ✅ ONVIF WS-Discovery + LAN sweep to find cameras/DVRs
- ✅ Default-credential self-audit (ISAPI HTTP Digest) → flags insecure devices
- ✅ Auto-built RTSP URLs; CLI (`scripts/discover_cameras.py`) + `POST /api/discovery/scan`
- ✅ RTSP connectivity tester (`scripts/test_camera.py`)

## Phase 2 — Analyzers (order = signal-to-effort)
- 🟡 `Analyzer` interface + pure pre/post-processing helpers
- ⏳ `PoseAnalyzer` (RTMPose / YOLO-pose) — runs first, feeds action + gait
- ⏳ `ReidAnalyzer` (OSNet / FastReID) — same-day cross-camera linking workhorse
- ⏳ `FaceAnalyzer` (InsightFace ArcFace buffalo_l, 512-d) — strongest ID evidence when visible
- ⏳ `ActionAnalyzer` (ST-GCN / CTR-GCN on pose windows) — loiter/fall/run/climb/fight
- ⏳ `GaitAnalyzer` (OpenGait GaitBase, silhouette) — **experimental**, hardest ONNX export

## Phase 3 — Profiling
- 🟡 `ProfileStore` — SQLite schema (persons, observations, embeddings, events, enrollments)
- 🟡 Per-modality cosine matching + explainable weighted fusion
- ⏳ Vector index swap (`sqlite-vec`/FAISS) when volume needs it
- ⏳ Merge/split review + correction feeds a learned re-ranker (later)

## Phase 4 — Web UI
- 🟡 FastAPI app shell (factory + lifespan + SPA fallback + SSE bus)
- ⏳ Live camera view + real-time detection overlay
- ⏳ Person gallery / profile page (face + re-ID + gait + behaviour timeline)
- ⏳ Behaviour alert feed
- ⏳ Enrollment flow (opt-in, name a cluster)
- ⏳ Retention / privacy settings surface

## Phase 4.5 — Alerting & polish
- ✅ Notifications: generic JSON webhook (ntfy / Home Assistant / Discord / Telegram / Slack)
- ✅ Alert filtering by event kind + per-subject cooldown (fights alert fatigue) + test endpoint
- ✅ Person thumbnails in the UI (latest crop per person)
- ✅ Crop-file retention enforced (PRIVACY.md promise) via the retention loop
- ⏳ Zones / virtual tripwires per camera (alert only inside a region) — next wave
- ⏳ Person detail page (cross-camera observation timeline)
- ⏳ Edit analyzer toggles / retention / notify from the UI (persisted)

## Phase 5 — Packaging
- ⏳ PyInstaller single-binary (backend serves built React SPA) — reuse bipolar-code spec
- ⏳ `docker-compose` bundling Frigate + MQTT + Argos
- ⏳ Model download UX in-app

## Cross-cutting
- ⏳ Benchmark analyzer throughput on RX 7800 XT; tune batch size + admission thresholds
- ⏳ fp16 pre-export pipeline for each model
- ⏳ Golden-frame regression tests per analyzer
