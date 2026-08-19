"""Face recognition embedding (InsightFace ArcFace).

ArcFace expects a **5-point-aligned** 112x112 face normalized to roughly [-1, 1]
(``(x - 127.5) / 127.5``), and outputs a 512-d embedding.

Note: good accuracy requires a face detector + aligner (e.g. RetinaFace/SCRFD) upstream to produce
the aligned face. On a raw person crop this degrades. Phase 2 wires the detector+aligner; until then
``FaceAnalyzer`` runs on the crop directly and is best treated as a coarse signal.
"""

from __future__ import annotations

import numpy as np

from argos.analyzers import preprocess
from argos.analyzers.base import EmbeddingAnalyzer


class FaceAnalyzer(EmbeddingAnalyzer):
    name = "face"
    modality = "face"
    input_size = (112, 112)  # ArcFace

    def _preprocess(self, crop: np.ndarray) -> np.ndarray:
        # ArcFace normalization differs from ImageNet: (x - 127.5) / 127.5, no per-channel std.
        resized = preprocess.resize_exact(crop, self.input_size).astype(np.float32)
        arr = (resized - 127.5) / 127.5
        return np.transpose(arr, (2, 0, 1))[np.newaxis, ...].copy()
