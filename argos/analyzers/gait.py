"""Gait recognition (OpenGait GaitBase, silhouette-based) — EXPERIMENTAL.

Gait is a soft biometric that survives clothing change and low face resolution, which makes it the
tie-breaker in identity fusion. It is also the hardest part:

- It needs a **silhouette sequence** for one track → a person-segmentation model must produce
  binary masks first. That segmentation model is not yet wired, so ``available`` stays ``False``
  until both the segmenter and the GaitBase ONNX export are present.
- GaitBase ONNX export is non-trivial (5-D tensors, ``einsum`` → opset ≥ 12); see docs/models.md.

The interface and the sequence→embedding path are in place so the model can drop in.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from argos.analyzers.base import Embedding
from argos.analyzers import preprocess
from argos.core.onnx_dml import get_session

_SILHOUETTE_SIZE = (64, 64)  # GaitBase default (w, h)


def normalize_silhouette(mask: np.ndarray) -> np.ndarray:
    """Binary mask → centered, resized silhouette (H, W) float32 in [0, 1]."""
    resized = cv2.resize(mask.astype(np.float32), _SILHOUETTE_SIZE, interpolation=cv2.INTER_LINEAR)
    return np.clip(resized / max(resized.max(), 1.0), 0.0, 1.0)


class GaitAnalyzer:
    name = "gait"
    modality = "gait"

    def __init__(self, model_path: str | Path, device: str, *, segmenter_available: bool = False) -> None:
        self._model_path = Path(model_path)
        self._device = device
        self._segmenter_available = segmenter_available

    @property
    def available(self) -> bool:
        # Needs BOTH the gait model AND a silhouette source (person segmenter).
        return self._model_path.is_file() and self._segmenter_available

    def analyze_sequence(self, silhouettes: list[np.ndarray]) -> Embedding | None:
        if not self.available or len(silhouettes) < 8:
            return None
        seq = np.stack([normalize_silhouette(m) for m in silhouettes])  # (T, H, W)
        tensor = seq[np.newaxis, ...].astype(np.float32)  # (1, T, H, W)
        loaded = get_session(self._model_path, self._device)
        input_name = loaded.session.get_inputs()[0].name  # type: ignore[attr-defined]
        outputs = loaded.session.run(None, {input_name: tensor})  # type: ignore[attr-defined]
        vector = preprocess.l2_normalize(np.asarray(outputs[0]).reshape(-1))
        return Embedding(modality=self.modality, vector=vector)
