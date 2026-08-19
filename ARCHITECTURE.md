# Argos — Architecture & Design Decisions

This document is the single source of truth for *why* Argos is shaped the way it is. It was
written up-front, before implementation, in place of an interactive design session. Where a
decision needed an owner's call that wasn't available, the assumption is recorded explicitly under
**Assumption** so it can be revisited.

---

## 1. Problem

Santiago has IP cameras wired to a Hikvision **HiLook DVR** on his home LAN. The goal is a
self-hosted system that goes beyond "there is a person in frame" and answers behavioural and
identity questions:

- **Who** is this person? Have we seen them before, on this or another camera?
- **What** are they doing? (walking, loitering, running, climbing, falling, fighting)
- **How** do they move? (gait as a soft biometric that survives clothing changes and low face res)
- Build a **profile / timeline** per person across cameras and days.

Constraints that shape everything below:

- **Hardware:** AMD Radeon RX 7800 XT (16 GB), Windows 11. No NVIDIA/CUDA. → inference must go
  through **ONNX Runtime + DirectML**, the exact path already proven in Upflow.
- **Privacy:** everything local, nothing leaves the LAN, opt-in enrollment. (See PRIVACY.md.)
- **Ecosystem fit:** reuse Upflow's ORT/DirectML core and VRAM admission control; reuse
  bipolar-code's FastAPI + React self-hosted-app scaffold.

---

## 2. Key decision: build the *analytics layer*, not another NVR

**Decision.** Do **not** re-implement RTSP ingest, motion, object detection, tracking, recording,
or a recordings UI. [Frigate](https://frigate.video) already does all of that well and, as of
0.16/0.17, also does face recognition, license-plate recognition and CLIP semantic search, with
first-class support for Coral / Hailo / Intel NPU / Apple Silicon detectors.

Argos occupies the layer **above** detection+tracking: pose, action/behaviour, cross-camera
re-identification, gait, and unified person profiling. That is precisely the gap Frigate does not
fill, and it is where the AMD GPU + ONNX/DirectML core adds value.

**Consequence.** The primary ingest path is a **Frigate consumer** (MQTT events + snapshot/clip
API). Frigate decodes the DVR's RTSP, picks the best crop of each tracked person, and hands Argos
a clean, deduplicated stream of "tracked person" events. Argos never touches raw H.264 in this
mode.

**Fallback.** For users without Frigate, a **direct RTSP** adapter pulls from the HiLook DVR and
runs its own person detector (YOLO-class, ONNX). Same downstream analyzers. This keeps Argos
useful standalone and keeps the two ingest paths behind one interface.

> **Assumption A1:** Frigate is the preferred ingest. If the owner would rather have Argos own the
> whole pipeline (no Frigate dependency), the direct-RTSP path is already there and can be promoted
> to primary; the analyzer/profiling layers don't change.

---

## 3. Component model

Three stable interfaces, everything else plugs into them:

### 3.1 `Ingestor` — produces `PersonObservation`s

An ingestor yields a stream of **person observations**: a cropped image of one tracked person, plus
metadata (camera id, timestamp, tracking id if known, bounding box, optional full frame for gait
silhouettes). Two implementations:

- `FrigateIngestor` — subscribes to `frigate/events` over MQTT, and on each tracked-object update
  fetches the best snapshot (`/api/events/<id>/snapshot.jpg`) or thumbnail. Tracking id = Frigate's
  event id, which is stable for the life of the object.
- `RtspIngestor` — an ffmpeg raw-`rgb24`-pipe frame source (adapted from Upflow's
  `FfmpegFrameSource`, with **RTSP-specific reconnect/backoff and frame-drop** added) feeding a
  built-in person detector + lightweight tracker to emit the same observations.

Both emit the same dataclass, so analyzers and profiling are ingest-agnostic.

### 3.2 `Analyzer` — turns an observation into a signal

Each analyzer consumes a `PersonObservation` and returns a typed result (an embedding vector, a
label + score, or a set of keypoints). Analyzers are independent and individually toggleable:

| Analyzer | Model family (ONNX) | Output | Notes |
|---|---|---|---|
| `PoseAnalyzer` | RTMPose / YOLO-pose | 17× keypoints | Feeds action + gait; cheap enough to run first. |
| `ActionAnalyzer` | ST-GCN / CTR-GCN on pose sequences | action label + score | Needs a **window** of poses per track (temporal). |
| `FaceAnalyzer` | InsightFace ArcFace (buffalo_l) | 512-d embedding | Only when a face is visible/large enough. |
| `ReidAnalyzer` | OSNet / FastReID | appearance embedding | Clothing-dependent; the workhorse for same-day linking. |
| `GaitAnalyzer` | OpenGait GaitBase (silhouette) | gait embedding | **Experimental** — needs a silhouette sequence; hardest to ONNX-export. |

Design rules for analyzers (mirrors the repo coding philosophy — atomic, testable, explicit deps):

- Pre/post-processing (letterbox, normalize, align, decode outputs) are **pure functions**, unit
  tested without a GPU.
- The ONNX session is injected, not constructed inside the analyzer, so admission control and the
  session cache stay centralized (see §4).
- An analyzer with no downloaded model returns `None`/`unavailable` cleanly — **never** silently
  fabricates a result. (Absence of signal is not a verdict — a lesson carried over from Upflow.)

### 3.3 `ProfileStore` — fuses signals into identities

The fusion problem: face, re-ID and gait each produce embeddings in **different spaces** with
different reliability and different invariances. We do **not** concatenate them. Instead:

- Each observation contributes zero or more embeddings, each tagged with its modality.
- Matching a new observation to known persons is done **per modality** (cosine similarity within
  the same space), then combined with a weighted, explainable rule:
  - **Face** match is strongest evidence (high precision when available).
  - **Gait** is the tie-breaker that survives clothing change and low face resolution.
  - **Re-ID** links within a short time window / same outfit (high recall, lower precision across
    days).
- A **person** is a cluster of observations. Fusion is intentionally conservative: prefer creating
  a new tentative identity over a wrong merge, and expose merges/splits in the UI for human review.

Storage: **SQLite** for structured data (persons, observations, events, enrollments) + a vector
index for the embeddings (start with brute-force cosine in NumPy per modality; swap to
`sqlite-vec`/FAISS when volume demands — the interface hides it). Retention limits are enforced
here (PRIVACY.md).

> **Assumption A2:** Start with explainable rule-based fusion, not a learned linker. It's debuggable,
> needs no training data, and the thresholds are visible/tunable. A learned re-ranker is a later
> optimization once there is labelled ground truth from the review UI.

### 3.4 Pipeline

`pipeline.py` is the orchestrator: `Ingestor → (Analyzers, gated by admission control) →
ProfileStore → events`. It owns the temporal windowing for `ActionAnalyzer`/`GaitAnalyzer`
(buffering a track's recent poses/silhouettes), applies per-analyzer enable flags, and publishes
resulting **events** (new person, recognized person, behaviour alert) to an in-process bus that the
API streams over SSE.

---

## 4. Inference core (ONNX Runtime + DirectML) — reused from Upflow

The single hardest-won asset here is Upflow's ORT/DirectML plumbing. Argos ports the **AMD-only
subset**:

- `build_providers(device)` → `[(DmlExecutionProvider, {device_id}), CPUExecutionProvider]`, with
  `dml:N` device parsing.
- `create_session(...)` + **`record_session_providers(...)`**: ORT can *silently* downgrade a DML
  session to CPU; the only way to know is to read `session.get_providers()` after creation. Argos
  surfaces this as a per-model `cpu_fallback` state in the UI — a slow analyzer is a bug we want
  visible, not hidden.
- **Cached sessions (LRU)** keyed by `(model_id, device)`: with 5 analyzer models sharing one 16 GB
  GPU, rebuilding sessions per call is a non-starter.
- **VRAM admission control** (DXGI `QueryVideoMemoryInfo` via ctypes, no extra deps): keeps N camera
  streams × M analyzers from OOMing the card. Upflow's `DeviceSemaphores` + `resource_probes` +
  `device_router` port over directly. Multi-camera analytics wants **batched** concurrency (batch
  several person crops into one `session.run`), which is a retune of Upflow's single-big-job
  defaults, not a rewrite.
- **fp16**: pre-export fp16 ONNX offline and select the fp16 file at load time (Upflow measured
  ~7× on its workload). No runtime casting.

Not ported (AMD-only target): the native TensorRT-RTX / OpenVINO plugin path. DirectML is the only
baseline we need.

> **Assumption A3:** Windows-only for the GPU path (matches the rig). The DXGI probe returns "unknown"
> (fail-open) off-Windows, and the CPU EP still runs, so Linux/dev works — just without VRAM gating.

---

## 5. Ingest specifics for HiLook / Hikvision

RTSP URL format (verified): `rtsp://user:pass@host:554/Streaming/Channels/<C>0<S>` where `C` is the
1-based channel and `S` is `1` (main/high-res) or `2` (sub/low-res). ISAPI snapshot:
`http://user:pass@host/ISAPI/Streaming/Channels/<C>01/picture`.

Practical rules baked into `RtspIngestor` (things a finite-file frame source doesn't need but a live
camera does):

- Use `-rtsp_transport tcp` (UDP loses packets → decode artifacts).
- **Detect on the sub-stream** (low-res, cheap), fetch the **main-stream** crop only when a person is
  confirmed. HiLook sub-streams are designed exactly for this.
- Reconnect with backoff on stream drop; **drop frames** under backpressure rather than growing
  latency (a bounded queue, newest-wins).

---

## 6. Web layer — reused from bipolar-code

- FastAPI **app factory + lifespan** composition root (start pipeline workers in `lifespan`,
  stash shared services on `app.state`).
- `core/config.py` (pydantic-settings + `@lru_cache`) and `core/logging.py` (structlog) copied in
  spirit.
- **SPA fallback** `StaticFiles` subclass to serve the built React app as one process, plus a
  PyInstaller spec for a single-binary distribution — same as bipolar-code.
- **Added, because bipolar-code is request/response only:** an **SSE** endpoint for live
  detections/alerts. Polling doesn't fit real-time camera events.
- Auth: API-key middleware (constant-time compare) is fine for a LAN box; documented as
  LAN-only. CORS is **not** left wide open (bipolar-code's `*` is tightened here).

---

## 7. Security & abuse posture

This is dual-use technology used on the owner's own premises. The codebase encodes the guardrails:

- **Local-only by construction**: no outbound calls in the data path; model downloads are the only
  network egress and are explicit/opt-in.
- **Opt-in enrollment**: no identity is *named* until a human enrolls it. Un-enrolled persons are
  anonymous cluster ids.
- **Retention limits** enforced in `ProfileStore`, configurable, defaulting conservative.
- **No covert-use affordances**: no evasion features, no third-party targeting, no dataset
  exfiltration. See PRIVACY.md for the lawful-use statement shipped to every operator.

---

## 8. What's deliberately out of scope (v1)

- License-plate recognition and CLIP semantic search — Frigate already does these; don't duplicate.
- Cloud sync, mobile push, multi-tenant — see the broader backlog; not this repo's job.
- A learned identity linker — starts rule-based (A2).
- Non-AMD accelerators — DirectML baseline only (A3).

---

## 9. Build order (see ROADMAP.md for detail)

1. Core: config, logging, ONNX/DML session factory + admission control. ✅ scaffolded
2. Ingest: dataclasses + Frigate adapter + RTSP adapter. ✅ scaffolded
3. Analyzers: pose → re-ID → face (highest signal-to-effort first). ⏳ interfaces + wiring
4. Profiling: store schema + rule-based fusion. ⏳ scaffolded
5. Action recognition (needs pose windows). ⏳
6. Gait (experimental, needs silhouettes). ⏳
7. UI: cameras, person gallery, timeline, alerts, enrollment.
