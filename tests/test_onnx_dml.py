import pytest

from argos.core import onnx_dml
from argos.core.onnx_dml import (
    CPU_PROVIDER,
    DML_PROVIDER,
    LoadedSession,
    SessionCache,
    build_providers,
    parse_dml_device_id,
)


def test_parse_dml_device_id():
    assert parse_dml_device_id("dml:0") == 0
    assert parse_dml_device_id("dml:2") == 2
    assert parse_dml_device_id("cpu") is None


def test_parse_dml_device_id_rejects_malformed():
    with pytest.raises(ValueError):
        parse_dml_device_id("dml:x")


def test_build_providers_cpu_and_dml():
    assert build_providers("cpu") == [CPU_PROVIDER]

    providers = build_providers("dml:1")

    assert providers[0] == (DML_PROVIDER, {"device_id": 1})
    assert providers[1] == CPU_PROVIDER


def test_cpu_fallback_detected_when_dml_runs_on_cpu():
    fell_back = LoadedSession(session=object(), providers=(CPU_PROVIDER,), model_path="m", device="dml:0")
    ran_on_gpu = LoadedSession(session=object(), providers=(DML_PROVIDER, CPU_PROVIDER), model_path="m", device="dml:0")

    assert fell_back.cpu_fallback is True
    assert ran_on_gpu.cpu_fallback is False


def test_session_cache_evicts_lru(monkeypatch):
    created = []

    def fake_create(path, device):
        created.append(path)
        return LoadedSession(session=object(), providers=(CPU_PROVIDER,), model_path=path, device=device)

    monkeypatch.setattr(onnx_dml, "_create_session", fake_create)
    cache = SessionCache(maxsize=2)

    cache.get("a", "cpu")
    cache.get("b", "cpu")
    cache.get("a", "cpu")  # a becomes most-recent
    cache.get("c", "cpu")  # evicts b (LRU)
    cache.get("a", "cpu")  # still cached → no rebuild

    assert created == ["a", "b", "c"]  # a was not rebuilt after eviction of b
