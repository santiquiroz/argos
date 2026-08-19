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


def query_free_vram_mb(adapter_index: int) -> int | None:
    """Free local VRAM (MB) for a DXGI adapter via ``IDXGIAdapter3::QueryVideoMemoryInfo``.

    Pure ctypes/COM, no dependencies. Fully guarded — any failure returns ``None`` (fail-open),
    never an exception, so a probe hiccup can't crash the pipeline. Windows-only.
    """
    if sys.platform != "win32":
        return None
    try:
        return _query_free_vram_mb_win(adapter_index)
    except Exception:  # noqa: BLE001 - fail-open on any COM/ctypes error
        return None


def _query_free_vram_mb_win(adapter_index: int) -> int | None:
    import ctypes
    from ctypes import POINTER, Structure, byref, c_uint, c_uint64, c_void_p, wintypes

    class GUID(Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    class MemInfo(Structure):
        _fields_ = [
            ("Budget", c_uint64),
            ("CurrentUsage", c_uint64),
            ("AvailableForReservation", c_uint64),
            ("CurrentReservation", c_uint64),
        ]

    iid_factory1 = GUID(0x770AAE78, 0xF26F, 0x4DBA, (0xA8, 0x29, 0x25, 0x3C, 0x83, 0xD1, 0xB3, 0x87))
    iid_adapter3 = GUID(0x645967A4, 0x1392, 0x4310, (0xA7, 0x98, 0x80, 0x53, 0xCE, 0x3E, 0x93, 0xFD))

    def vmethod(obj, index, *argtypes):
        vtbl = ctypes.cast(obj, POINTER(c_void_p))[0]
        func = ctypes.cast(vtbl, POINTER(c_void_p))[index]
        return ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, *argtypes)(func)

    def release(obj):
        if obj:
            ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)(
                ctypes.cast(ctypes.cast(obj, POINTER(c_void_p))[0], POINTER(c_void_p))[2]
            )(obj)

    dxgi = ctypes.windll.dxgi
    dxgi.CreateDXGIFactory1.argtypes = [POINTER(GUID), POINTER(c_void_p)]
    dxgi.CreateDXGIFactory1.restype = ctypes.HRESULT

    factory = c_void_p()
    dxgi.CreateDXGIFactory1(byref(iid_factory1), byref(factory))
    adapter = c_void_p()
    adapter3 = c_void_p()
    try:
        # EnumAdapters1 = vtable[12]; QueryInterface = vtable[0]; QueryVideoMemoryInfo = vtable[14].
        vmethod(factory, 12, c_uint, POINTER(c_void_p))(factory, adapter_index, byref(adapter))
        vmethod(adapter, 0, POINTER(GUID), POINTER(c_void_p))(adapter, byref(iid_adapter3), byref(adapter3))
        info = MemInfo()
        vmethod(adapter3, 14, c_uint, c_uint, POINTER(MemInfo))(adapter3, 0, 0, byref(info))
        free_bytes = max(0, int(info.Budget) - int(info.CurrentUsage))
        return free_bytes // (1024 * 1024)
    finally:
        release(adapter3)
        release(adapter)
        release(factory)


class VramProbe:
    """Free VRAM for a DirectML adapter via DXGI (fail-open)."""

    def __init__(self, device_id: int) -> None:
        self._device_id = device_id

    def free_mb(self) -> int | None:
        return query_free_vram_mb(self._device_id)


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
