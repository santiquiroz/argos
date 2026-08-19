"""Action / behaviour recognition (ST-GCN on pose sequences).

Consumes a *window* of poses for one track (not a single crop), so it is driven by the pipeline's
per-track pose buffer rather than the single-crop ``Analyzer`` interface. Detects behaviours like
loitering, falling, running, climbing, fighting — the action set depends on the trained model; the
NTU-trained defaults must be relabelled/retrained for a security-specific set.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from argos.core.onnx_dml import get_session

# Placeholder label set; replace with your model's classes (see docs/models.md).
DEFAULT_LABELS = ("standing", "walking", "running", "falling", "loitering", "climbing", "fighting")


@dataclass(frozen=True, slots=True)
class ActionResult:
    label: str
    score: float


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    return exp / np.sum(exp)


def _build_stgcn_input(keypoints_seq: list[np.ndarray], window: int) -> np.ndarray:
    """List of ``(V, 3)`` keypoints → ST-GCN tensor ``(1, C=3, T=window, V, M=1)``.

    Pads/truncates to ``window`` frames and centers coords per frame for translation invariance.
    """
    joints = keypoints_seq[0].shape[0]
    frames = keypoints_seq[-window:]
    tensor = np.zeros((3, window, joints, 1), dtype=np.float32)
    offset = window - len(frames)
    for t, kp in enumerate(frames):
        xy = kp[:, :2]
        center = xy[kp[:, 2] > 0.1].mean(axis=0) if np.any(kp[:, 2] > 0.1) else xy.mean(axis=0)
        tensor[0, offset + t, :, 0] = xy[:, 0] - center[0]
        tensor[1, offset + t, :, 0] = xy[:, 1] - center[1]
        tensor[2, offset + t, :, 0] = kp[:, 2]
    return tensor[np.newaxis, ...]


class ActionAnalyzer:
    name = "action"

    def __init__(self, model_path: str | Path, device: str, *, labels: tuple[str, ...] = DEFAULT_LABELS, window: int = 30) -> None:
        self._model_path = Path(model_path)
        self._device = device
        self._labels = labels
        self._window = window

    @property
    def available(self) -> bool:
        return self._model_path.is_file()

    def analyze_sequence(self, keypoints_seq: list[np.ndarray]) -> ActionResult | None:
        if not self.available or len(keypoints_seq) < 2:
            return None
        tensor = _build_stgcn_input(keypoints_seq, self._window)
        loaded = get_session(self._model_path, self._device)
        input_name = loaded.session.get_inputs()[0].name  # type: ignore[attr-defined]
        logits = loaded.session.run(None, {input_name: tensor})[0].reshape(-1)  # type: ignore[attr-defined]
        probs = _softmax(logits)
        idx = int(np.argmax(probs))
        label = self._labels[idx] if idx < len(self._labels) else f"class_{idx}"
        return ActionResult(label=label, score=float(probs[idx]))
