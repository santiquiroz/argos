"""YOLO person detector (ONNX) for the direct-RTSP path.

Ultralytics-style output: ``(1, 84, 8400)`` = 4 box coords + 80 class scores per anchor (no separate
objectness). We keep class 0 (``person``), map boxes back through the letterbox, and NMS.

Runs on the DirectML/AMD path via the shared session cache. Missing model file → ``available=False``.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from argos.analyzers import preprocess
from argos.core.onnx_dml import get_session
from argos.logging import get_logger

log = get_logger(__name__)

_PERSON_CLASS = 0
Box = tuple[int, int, int, int, float]  # x1, y1, x2, y2, score


def _as_anchors_first(pred: np.ndarray) -> np.ndarray:
    """Normalize model output to ``(num_anchors, 4 + num_classes)``.

    Drops the batch dim explicitly (not ``squeeze``, which would collapse a degenerate
    single-anchor axis too). Real YOLO output has far more anchors than features, so the smaller
    axis is the feature axis.
    """
    pred = np.asarray(pred)
    if pred.ndim == 3:
        pred = pred[0]
    # (84, N) → (N, 84); leave (N, 84) as-is.
    if pred.shape[0] < pred.shape[1]:
        pred = pred.transpose(1, 0)
    return pred


def _xywh_to_xyxy(boxes: np.ndarray) -> np.ndarray:
    xy = boxes[:, :2]
    half = boxes[:, 2:4] / 2.0
    return np.concatenate([xy - half, xy + half], axis=1)


def decode(pred: np.ndarray, scale: float, pad: tuple[int, int], frame_shape: tuple[int, int], *, conf_thres: float, iou_thres: float) -> list[Box]:
    """YOLO output → person boxes in original-frame pixels."""
    anchors = _as_anchors_first(pred)
    class_scores = anchors[:, 4:]
    class_ids = np.argmax(class_scores, axis=1)
    confidences = np.max(class_scores, axis=1)
    keep = (class_ids == _PERSON_CLASS) & (confidences >= conf_thres)
    if not np.any(keep):
        return []
    boxes_xyxy = _xywh_to_xyxy(anchors[keep, :4])
    scores = confidences[keep]
    boxes_mapped = _unletterbox(boxes_xyxy, scale, pad, frame_shape)
    return _nms(boxes_mapped, scores, conf_thres, iou_thres)


def _unletterbox(boxes: np.ndarray, scale: float, pad: tuple[int, int], frame_shape: tuple[int, int]) -> np.ndarray:
    pad_x, pad_y = pad
    h, w = frame_shape
    out = boxes.copy()
    out[:, [0, 2]] = np.clip((out[:, [0, 2]] - pad_x) / scale, 0, w)
    out[:, [1, 3]] = np.clip((out[:, [1, 3]] - pad_y) / scale, 0, h)
    return out


def _nms(boxes_xyxy: np.ndarray, scores: np.ndarray, conf_thres: float, iou_thres: float) -> list[Box]:
    wh = boxes_xyxy[:, 2:4] - boxes_xyxy[:, :2]
    rects = np.concatenate([boxes_xyxy[:, :2], wh], axis=1).tolist()  # x, y, w, h for cv2
    indices = cv2.dnn.NMSBoxes(rects, scores.tolist(), conf_thres, iou_thres)
    if len(indices) == 0:
        return []
    result: list[Box] = []
    for i in np.array(indices).flatten():
        x1, y1, x2, y2 = boxes_xyxy[i].astype(int)
        result.append((int(x1), int(y1), int(x2), int(y2), float(scores[i])))
    return result


class YoloPersonDetector:
    input_size = (640, 640)

    def __init__(self, model_path: str | Path, device: str, *, conf_thres: float = 0.35, iou_thres: float = 0.5) -> None:
        self._model_path = Path(model_path)
        self._device = device
        self._conf = conf_thres
        self._iou = iou_thres

    @property
    def available(self) -> bool:
        return self._model_path.is_file()

    def detect(self, frame: np.ndarray) -> list[Box]:
        canvas, scale, pad = preprocess.letterbox(frame, self.input_size)
        tensor = preprocess.to_nchw_float(canvas, normalize=False)
        loaded = get_session(self._model_path, self._device)
        input_name = loaded.session.get_inputs()[0].name  # type: ignore[attr-defined]
        pred = loaded.session.run(None, {input_name: tensor})[0]  # type: ignore[attr-defined]
        return decode(pred, scale, pad, frame.shape[:2], conf_thres=self._conf, iou_thres=self._iou)
