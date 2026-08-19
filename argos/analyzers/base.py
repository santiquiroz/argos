"""Analyzer contract + shared embedding-analyzer base.

An analyzer is independent and individually toggleable. It loads its ONNX model lazily via the
shared session cache, and — importantly — reports ``available == False`` and returns ``None`` when
its model isn't present, rather than fabricating a result. (Absence of signal is not a verdict.)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from argos.analyzers import preprocess
from argos.core.onnx_dml import LoadedSession, get_session
from argos.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Embedding:
    """An L2-normalized feature vector tagged with the modality that produced it."""

    modality: str  # "face" | "reid" | "gait"
    vector: np.ndarray


@dataclass(frozen=True, slots=True)
class AnalyzerResult:
    """What an analyzer returns for one observation. Fields are populated per analyzer type."""

    analyzer: str
    embedding: Embedding | None = None
    keypoints: np.ndarray | None = None  # (K, 3): x, y, score
    label: str | None = None
    score: float | None = None


class Analyzer(ABC):
    name: str = "analyzer"

    @property
    @abstractmethod
    def available(self) -> bool:
        """True if the analyzer can run (model present, session loadable)."""

    @abstractmethod
    def analyze(self, crop: np.ndarray) -> AnalyzerResult | None:
        """Analyze a person crop (RGB HxWx3 uint8). ``None`` when unavailable/not applicable."""


class EmbeddingAnalyzer(Analyzer):
    """Base for face/re-ID/gait: preprocess → ``session.run`` → L2-normalize.

    Subclasses set ``name``, ``modality``, ``input_size`` and implement ``_preprocess``.
    """

    modality: str = "reid"
    input_size: tuple[int, int] = (128, 256)  # (w, h)

    def __init__(self, model_path: str | Path, device: str) -> None:
        self._model_path = Path(model_path)
        self._device = device

    @property
    def available(self) -> bool:
        return self._model_path.is_file()

    def _session(self) -> LoadedSession:
        return get_session(self._model_path, self._device)

    def _preprocess(self, crop: np.ndarray) -> np.ndarray:
        """RGB crop → model input tensor. Override per model."""
        resized = preprocess.resize_exact(crop, self.input_size)
        return preprocess.to_nchw_float(resized, normalize=True)

    def analyze(self, crop: np.ndarray) -> AnalyzerResult | None:
        if not self.available or crop is None or crop.size == 0:
            return None
        loaded = self._session()
        tensor = self._preprocess(crop)
        input_name = loaded.session.get_inputs()[0].name  # type: ignore[attr-defined]
        outputs = loaded.session.run(None, {input_name: tensor})  # type: ignore[attr-defined]
        vector = preprocess.l2_normalize(np.asarray(outputs[0]).reshape(-1))
        return AnalyzerResult(
            analyzer=self.name,
            embedding=Embedding(modality=self.modality, vector=vector),
        )
