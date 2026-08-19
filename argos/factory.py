"""Compose the ingestor and analyzers from settings + on-disk model files.

Model files are expected at ``<models_dir>/<name>.onnx`` (and optionally ``<name>_fp16.onnx``,
preferred on the DirectML path). A missing file just means that analyzer reports ``available=False``
and is skipped — the app still runs.
"""

from __future__ import annotations

from pathlib import Path

from argos.analyzers.action import ActionAnalyzer
from argos.analyzers.base import Analyzer
from argos.analyzers.face import FaceAnalyzer
from argos.analyzers.pose import PoseAnalyzer
from argos.analyzers.reid import ReidAnalyzer
from argos.config import Settings
from argos.ingest.base import Ingestor
from argos.ingest.frigate import FrigateIngestor
from argos.ingest.rtsp import RtspIngestor


def resolve_model_path(models_dir: Path, name: str, *, prefer_fp16: bool) -> Path:
    """Prefer ``<name>_fp16.onnx`` when present and requested, else ``<name>.onnx``."""
    if prefer_fp16:
        fp16 = models_dir / f"{name}_fp16.onnx"
        if fp16.is_file():
            return fp16
    return models_dir / f"{name}.onnx"


def build_ingestor(settings: Settings) -> Ingestor:
    if settings.ingest == "rtsp":
        return RtspIngestor(settings, _build_detector(settings))
    return FrigateIngestor(settings)


def _build_detector(settings: Settings):
    from argos.detect.yolo import YoloPersonDetector

    path = resolve_model_path(settings.models_dir, "detector", prefer_fp16=settings.prefer_fp16)
    return YoloPersonDetector(path, settings.device)


def build_crop_analyzers(settings: Settings) -> list[Analyzer]:
    models_dir = settings.models_dir
    device = settings.device
    candidates: list[tuple[bool, Analyzer]] = [
        (settings.enable_pose, PoseAnalyzer(resolve_model_path(models_dir, "pose", prefer_fp16=settings.prefer_fp16), device)),
        (settings.enable_reid, ReidAnalyzer(resolve_model_path(models_dir, "reid", prefer_fp16=settings.prefer_fp16), device)),
        (settings.enable_face, FaceAnalyzer(resolve_model_path(models_dir, "face", prefer_fp16=settings.prefer_fp16), device)),
    ]
    return [analyzer for enabled, analyzer in candidates if enabled]


def build_action_analyzer(settings: Settings) -> ActionAnalyzer | None:
    if not settings.enable_action:
        return None
    path = resolve_model_path(settings.models_dir, "action", prefer_fp16=settings.prefer_fp16)
    return ActionAnalyzer(path, settings.device)
