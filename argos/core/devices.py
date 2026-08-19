"""GPU capacity detection + admission control.

Keeps N camera streams × M analyzer models from OOMing a single 16 GB GPU. Structure ported from
Upflow (``resource_probes`` + ``device_semaphores``):

- A ``ResourceProbe`` reports free capacity; ``None`` means "unknown" → **fail-open** (never block on
  a probe we can't read).
- ``AdmissionGate`` combines a per-device concurrency count with a min-free-VRAM threshold.

The real DXGI ``QueryVideoMemoryInfo`` (ctypes/COM, no deps) lives in Upflow
``app/services/devices_service.py::_query_video_memory_info_mb`` and should be ported verbatim — it
is tested there. Until then ``VramProbe`` reports ``None`` (fail-open), so the concurrency limit is
the only active constraint. That is safe: worst case is one extra concurrent job, not a crash.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Protocol

from argos.logging import get_logger

log = get_logger(__name__)


class ResourceProbe(Protocol):
    def free_mb(self) -> int | None:
        """Free capacity in MB, or ``None`` if unknown (fail-open)."""
        ...


class NullProbe:
    def free_mb(self) -> int | None:
        return None


class VramProbe:
    """Free VRAM for a DirectML adapter.

    TODO(port): bring over Upflow's tested DXGI ``QueryVideoMemoryInfo`` ctypes implementation.
    Shipping untested COM vtable calls risks an access violation, so this fails open for now.
    """

    def __init__(self, device_id: int) -> None:
        self._device_id = device_id

    def free_mb(self) -> int | None:
        if sys.platform != "win32":
            return None
        return None  # fail-open until the DXGI probe is ported


def make_probe(device: str) -> ResourceProbe:
    from argos.core.onnx_dml import parse_dml_device_id

    device_id = parse_dml_device_id(device)
    if device_id is None:
        return NullProbe()
    return VramProbe(device_id)


class AdmissionGate:
    """Async admission control for one compute device.

    Grants a slot when concurrency is below the cap *and* (when the probe knows) free VRAM is above
    the threshold. Use as an async context manager around each ``session.run``.
    """

    def __init__(self, *, concurrency: int, min_free_mb: int, probe: ResourceProbe) -> None:
        self._cap = max(1, concurrency)
        self._min_free_mb = min_free_mb
        self._probe = probe
        self._in_flight = 0
        self._cond = asyncio.Condition()

    def _has_capacity(self) -> bool:
        if self._in_flight >= self._cap:
            return False
        free = self._probe.free_mb()
        if free is None:  # unknown → fail-open
            return True
        return free >= self._min_free_mb

    async def acquire(self) -> None:
        async with self._cond:
            # Poll on a timeout too: VRAM freed by an external process never notifies us.
            while not self._has_capacity():
                try:
                    await asyncio.wait_for(self._cond.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
            self._in_flight += 1

    async def release(self) -> None:
        async with self._cond:
            self._in_flight = max(0, self._in_flight - 1)
            self._cond.notify_all()

    async def __aenter__(self) -> AdmissionGate:
        await self.acquire()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.release()
