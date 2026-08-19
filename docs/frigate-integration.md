# Ingest: Frigate vs. direct RTSP

Argos supports two ingest paths behind one `Ingestor` interface. Pick per your setup; the analyzers
and profiling downstream are identical.

## Path A — Frigate consumer (recommended)

Frigate decodes the HiLook DVR's RTSP, runs object detection + tracking, and picks the best crop of
each tracked person. Argos subscribes to Frigate's events and pulls those crops — no H.264 decoding
in Argos.

### How it works

1. Frigate publishes to MQTT topic `frigate/events` on every tracked-object state change. Payload:
   `{ "type": "new"|"update"|"end", "before": {...}, "after": { "id", "camera", "label",
   "current_zones", "box", "snapshot", ... } }`.
2. `FrigateIngestor` filters `after.label == "person"`, and on `new`/`update` fetches the best
   snapshot: `GET http://<frigate>/api/events/<id>/snapshot.jpg` (or `thumbnail.jpg`). The event
   `id` is a **stable tracking id** for the life of the object.
3. Argos emits a `PersonObservation(track_id=<event id>, camera=<after.camera>, crop=<snapshot>, …)`.

### Config (`.env`)

```
ARGOS_INGEST=frigate
ARGOS_FRIGATE_URL=http://frigate.lan:5000
ARGOS_MQTT_HOST=frigate.lan
ARGOS_MQTT_PORT=1883
# ARGOS_MQTT_USER=...
# ARGOS_MQTT_PASSWORD=...
```

Enable snapshots in Frigate (`snapshots: enabled: true` per camera) so the snapshot API has images.

### Why this is preferred

Frigate has already solved reconnect, decode, motion gating, tracking and best-frame selection.
Argos gets clean, deduplicated person crops and spends its GPU budget on the analytics that Frigate
doesn't do.

## Path B — Direct RTSP (no Frigate)

Argos pulls RTSP straight from the HiLook DVR and runs its own person detector.

### HiLook / Hikvision RTSP URLs

```
Main stream (channel C):  rtsp://user:pass@host:554/Streaming/Channels/<C>01
Sub  stream (channel C):  rtsp://user:pass@host:554/Streaming/Channels/<C>02
ISAPI snapshot:           http://user:pass@host/ISAPI/Streaming/Channels/<C>01/picture
```

`C` is the 1-based channel (`1`,`2`,…). Trailing `01` = main/high-res, `02` = sub/low-res. Ensure
RTSP (and ONVIF, if used) is enabled and a camera user exists in the DVR web UI.

### How `RtspIngestor` works

- ffmpeg pulls the stream as raw `rgb24` frames over a stdout pipe (`-rtsp_transport tcp` — UDP
  drops packets). Adapted from Upflow's `FfmpegFrameSource`, plus **reconnect/backoff** and a
  **bounded newest-wins queue** so latency never grows under load.
- **Two-stream strategy:** run the person detector on the cheap **sub-stream**; when a person is
  confirmed, fetch the **main-stream** crop for the analyzers (higher res → better face/re-ID/gait).
- A lightweight tracker assigns stable `track_id`s so temporal analyzers (action, gait) can window.

### Config (`.env`)

```
ARGOS_INGEST=rtsp
ARGOS_RTSP_CAMERAS=front=rtsp://user:pass@dvr.lan:554/Streaming/Channels/102;yard=rtsp://user:pass@dvr.lan:554/Streaming/Channels/202
# name=url pairs, ';'-separated. Point at sub-streams (…02) for detection.
```

## Which to choose

| | Frigate consumer | Direct RTSP |
|---|---|---|
| Extra services | Frigate + MQTT | none |
| Decode / motion / tracking | Frigate | Argos (ffmpeg + own detector) |
| GPU load in Argos | analyzers only | detector + analyzers |
| Best-frame selection | Frigate's | Argos' |
| Recommended for | most users | minimal setups / no Frigate |
