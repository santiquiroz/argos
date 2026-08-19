"""Pure pre/post-processing helpers. No GPU, no I/O — fully unit-testable.

Keeping these pure is deliberate: the fiddly, bug-prone geometry and normalization live here and are
covered by tests, while the analyzers just wire them to an ONNX session.
"""

from __future__ import annotations

import cv2
import numpy as np

# ImageNet normalization (torchreid / most backbones).
_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def letterbox(image: np.ndarray, size: tuple[int, int], pad_value: int = 114) -> tuple[np.ndarray, float, tuple[int, int]]:
    """Resize keeping aspect ratio, pad to ``size`` (w, h). Returns (image, scale, (pad_x, pad_y))."""
    target_w, target_h = size
    h, w = image.shape[:2]
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((target_h, target_w, 3), pad_value, dtype=image.dtype)
    pad_x, pad_y = (target_w - new_w) // 2, (target_h - new_h) // 2
    canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
    return canvas, scale, (pad_x, pad_y)


def resize_exact(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Resize to exactly ``size`` (w, h), ignoring aspect ratio (re-ID convention)."""
    return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)


def to_nchw_float(image: np.ndarray, *, normalize: bool = True) -> np.ndarray:
    """RGB HxWx3 uint8 → 1x3xHxW float32, optionally ImageNet-normalized."""
    arr = image.astype(np.float32) / 255.0
    if normalize:
        arr = (arr - _IMAGENET_MEAN) / _IMAGENET_STD
    return np.transpose(arr, (2, 0, 1))[np.newaxis, ...].copy()


def l2_normalize(vec: np.ndarray, eps: float = 1e-10) -> np.ndarray:
    """Unit-normalize a 1-D embedding so cosine similarity == dot product."""
    norm = float(np.linalg.norm(vec))
    return vec / (norm + eps)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity of two 1-D vectors, in [-1, 1]."""
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)
