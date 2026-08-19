"""ONNX Runtime + DirectML session factory (AMD-only subset, ported from Upflow).

Two hard-won behaviours are preserved from Upflow:

1. ``dml:N`` device parsing → provider list ``[(DmlExecutionProvider, {device_id}), CPU]``.
2. **Silent CPU-fallback detection**: ORT can downgrade a DirectML session to CPU without error;
   the only way to know is to read ``session.get_providers()`` after creation. A slow analyzer is a
   bug we want visible, so ``create_session`` records the *actual* providers.

Sessions are expensive to build and several analyzer models share one 16 GB GPU, so sessions are
cached with an LRU keyed by ``(model_path, device)``.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from argos.logging import get_logger

log = get_logger(__name__)

DML_PROVIDER = "DmlExecutionProvider"
CPU_PROVIDER = "CPUExecutionProvider"
DML_PREFIX = "dml:"

_CACHE_MAX = 6  # detector + pose + face + reid + action + gait


def parse_dml_device_id(device: str) -> int | None:
    """``"dml:1"`` → ``1``. Returns ``None`` for non-DML devices."""
    if not device.startswith(DML_PREFIX):
        return None
    try:
        return int(device[len(DML_PREFIX):])
    except ValueError as exc:
        raise ValueError(f"invalid DirectML device {device!r}, expected 'dml:N'") from exc


def build_providers(device: str) -> list:
    """Provider list for a device string. CPU-only for ``"cpu"``, DML+CPU fallback otherwise."""
    if device == "cpu":
        return [CPU_PROVIDER]
    device_id = parse_dml_device_id(device)
    if device_id is None:
        raise ValueError(f"unknown device {device!r}, expected 'dml:N' or 'cpu'")
    return [(DML_PROVIDER, {"device_id": device_id}), CPU_PROVIDER]


@dataclass(frozen=True)
class LoadedSession:
    """A wrapped ORT session plus the providers it *actually* bound to."""

    session: object  # onnxruntime.InferenceSession
    providers: tuple[str, ...]
    model_path: str
    device: str

    @property
    def cpu_fallback(self) -> bool:
        """True if a DML device silently ran on CPU."""
        return self.device != "cpu" and DML_PROVIDER not in self.providers


def _import_ort():
    try:
        import onnxruntime as ort  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "onnxruntime is not installed. Install extras: "
            "pip install 'argos-vision[directml]' (AMD GPU) or 'argos-vision[cpu]'."
        ) from exc
    return ort


def _make_session_options(ort) -> object:
    opts = ort.SessionOptions()
    # DirectML prefers sequential execution and no memory-pattern reuse.
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    opts.enable_mem_pattern = False
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return opts


def _create_session(model_path: str, device: str) -> LoadedSession:
    ort = _import_ort()
    session = ort.InferenceSession(
        model_path,
        sess_options=_make_session_options(ort),
        providers=build_providers(device),
    )
    providers = tuple(session.get_providers())
    loaded = LoadedSession(session=session, providers=providers, model_path=model_path, device=device)
    if loaded.cpu_fallback:
        log.warning("onnx_cpu_fallback", model=Path(model_path).name, device=device, providers=providers)
    else:
        log.info("onnx_session_ready", model=Path(model_path).name, device=device, providers=providers)
    return loaded


class SessionCache:
    """Thread-safe LRU of loaded ORT sessions keyed by ``(model_path, device)``."""

    def __init__(self, maxsize: int = _CACHE_MAX) -> None:
        self._maxsize = maxsize
        self._lock = threading.Lock()
        self._store: OrderedDict[tuple[str, str], LoadedSession] = OrderedDict()

    def get(self, model_path: str | Path, device: str) -> LoadedSession:
        key = (str(model_path), device)
        with self._lock:
            cached = self._store.get(key)
            if cached is not None:
                self._store.move_to_end(key)
                return cached
        # Build outside the lock — session construction is slow.
        loaded = _create_session(str(model_path), device)
        with self._lock:
            self._store[key] = loaded
            self._store.move_to_end(key)
            while len(self._store) > self._maxsize:
                evicted_key, _ = self._store.popitem(last=False)
                log.info("onnx_session_evicted", model=Path(evicted_key[0]).name, device=evicted_key[1])
        return loaded

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


_default_cache = SessionCache()


def get_session(model_path: str | Path, device: str) -> LoadedSession:
    """Module-level convenience over the default cache."""
    return _default_cache.get(model_path, device)
