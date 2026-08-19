# Model registry

Argos does **not** bundle model weights. Each analyzer loads an ONNX model you download yourself via
`scripts/download_models.py`, driven by [`models/registry.yaml`](../models/registry.yaml). Each model
carries its **own license** — some are research / non-commercial only. **Read the license column
before using a model in anything beyond personal experimentation.**

```bash
python scripts/download_models.py --list          # show catalog + license + status
python scripts/download_models.py pose reid face  # download by task
```

Downloads land in `ARGOS_MODELS_DIR` (default `./models/weights/`), verified against the SHA-256 in
the registry.

## Catalog

| Task | Default model | Format | Approx size | License | Notes |
|---|---|---|---|---|---|
| **Person detection** (direct-RTSP path) | YOLO-class (e.g. YOLO26-n/RT-DETR) | ONNX | 10–40 MB | model-specific (often AGPL/Apache — check) | Only needed if you don't use Frigate. |
| **Pose** | RTMPose-m (body 17kp) or YOLO-pose | ONNX | 6–50 MB | Apache-2.0 (RTMPose/mmpose) | Runs first; feeds action + gait. |
| **Face** | InsightFace ArcFace `buffalo_l` | ONNX | ~250 MB pack | **InsightFace models: non-commercial research** | 512-d embedding. Check terms for any commercial use. |
| **Re-ID** | OSNet (`osnet_x1_0`) or FastReID | ONNX | 10–100 MB | Apache-2.0 (torchreid) / Apache-2.0 (FastReID) | Appearance embedding. |
| **Gait** (experimental) | OpenGait GaitBase | ONNX | 10–40 MB | OpenGait license (research) | Silhouette-based; export is non-trivial (5-D tensors, `einsum` → opset ≥ 12). |
| **Action** | ST-GCN / CTR-GCN (NTU-trained) | ONNX | 5–20 MB | model-specific | On pose windows; retrain/relabel to your action set. |

## fp16

For the DirectML/AMD path, export an **fp16** ONNX file alongside the fp32 one and Argos will prefer
it at load time (Upflow measured ~7× on its workload). Use the `onnxruntime.transformers.float16`
converter, keep normalization layers in fp32, and re-run `topological_sort` after conversion (see
the Upflow fp16/DirectML notes). Runtime casting is intentionally not done.

## ONNX export gotchas (carried over from Upflow experience)

- Don't trust ONNX input/output **shape metadata** — it's often dynamic/symbolic. Derive real
  shapes from an actual inference on a probe input.
- ST-GCN / gait models use `einsum` and 5-D tensors → export with **opset ≥ 12** or rewrite the op.
- After any fp16 conversion, delete stale `value_info` and re-`topological_sort`; `onnx.save`
  **appends** to an existing external-data file rather than replacing it.
- After creating a DirectML session, always read `session.get_providers()` — ORT can silently fall
  back to CPU. Argos does this in `create_session` and reports it.
