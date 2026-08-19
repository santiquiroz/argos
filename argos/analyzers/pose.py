"""Pose estimation (RTMPose, SimCC head).

Runs first: keypoints feed both the action analyzer (temporal pose graph) and the gait analyzer
(silhouette assist). Implements the RTMPose SimCC decode — model outputs per-keypoint 1-D
distributions over x and y, argmax gives sub-pixel coords.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from argos.analyzers import preprocess
from argos.analyzers.base import Analyzer, AnalyzerResult
from argos.core.onnx_dml import get_session

# RTMPose normalization (RGB, 0-255).
_MEAN = np.array([123.675, 116.28, 103.53], dtype=np.float32)
_STD = np.array([58.395, 57.12, 57.375], dtype=np.float32)
_SIMCC_SPLIT = 2.0


def _preprocess_rtmpose(crop: np.ndarray, size: tuple[int, int]) -> tuple[np.ndarray, float, tuple[int, int]]:
    canvas, scale, pad = preprocess.letterbox(crop, size, pad_value=114)
    arr = (canvas.astype(np.float32) - _MEAN) / _STD
    tensor = np.transpose(arr, (2, 0, 1))[np.newaxis, ...].copy()
    return tensor, scale, pad


def _decode_simcc(simcc_x: np.ndarray, simcc_y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """SimCC outputs → keypoint coords (in input pixels) and per-keypoint scores."""
    x_locs = np.argmax(simcc_x, axis=-1).astype(np.float32)  # (K,)
    y_locs = np.argmax(simcc_y, axis=-1).astype(np.float32)
    x_conf = np.max(simcc_x, axis=-1)
    y_conf = np.max(simcc_y, axis=-1)
    coords = np.stack([x_locs / _SIMCC_SPLIT, y_locs / _SIMCC_SPLIT], axis=-1)  # (K, 2)
    scores = np.minimum(x_conf, y_conf)
    return coords, scores


def _map_to_crop(coords: np.ndarray, scale: float, pad: tuple[int, int]) -> np.ndarray:
    pad_x, pad_y = pad
    mapped = coords.copy()
    mapped[:, 0] = (mapped[:, 0] - pad_x) / scale
    mapped[:, 1] = (mapped[:, 1] - pad_y) / scale
    return mapped


class PoseAnalyzer(Analyzer):
    name = "pose"
    input_size = (192, 256)  # RTMPose-m body (w, h)

    def __init__(self, model_path: str | Path, device: str) -> None:
        self._model_path = Path(model_path)
        self._device = device

    @property
    def available(self) -> bool:
        return self._model_path.is_file()

    def analyze(self, crop: np.ndarray) -> AnalyzerResult | None:
        if not self.available or crop is None or crop.size == 0:
            return None
        loaded = self._session_run(crop)
        return loaded

    def _session_run(self, crop: np.ndarray) -> AnalyzerResult:
        loaded = get_session(self._model_path, self._device)
        tensor, scale, pad = _preprocess_rtmpose(crop, self.input_size)
        input_name = loaded.session.get_inputs()[0].name  # type: ignore[attr-defined]
        simcc_x, simcc_y = loaded.session.run(None, {input_name: tensor})  # type: ignore[attr-defined]
        coords, scores = _decode_simcc(simcc_x[0], simcc_y[0])
        coords = _map_to_crop(coords, scale, pad)
        keypoints = np.concatenate([coords, scores[:, None]], axis=-1)  # (K, 3)
        return AnalyzerResult(analyzer=self.name, keypoints=keypoints)


def draw_keypoints(crop: np.ndarray, keypoints: np.ndarray, threshold: float = 0.3) -> np.ndarray:
    """Debug overlay: draw keypoints above ``threshold``. Returns a copy."""
    out = crop.copy()
    for x, y, s in keypoints:
        if s >= threshold:
            cv2.circle(out, (int(x), int(y)), 3, (0, 255, 0), -1)
    return out
