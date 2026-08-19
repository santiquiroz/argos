from argos.config import Settings
from argos.events import EventBus
from argos.ingest.base import Ingestor, PersonObservation
from argos.pipeline import Pipeline
from argos.profiling.store import ProfileStore
from argos.zones import Zone, ZoneStore

SQUARE = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


class _DummyIngestor(Ingestor):
    def observations(self):
        async def _gen():
            if False:  # pragma: no cover
                yield
        return _gen()

    async def close(self):
        pass


def _pipeline(zone_store: ZoneStore, store: ProfileStore) -> Pipeline:
    return Pipeline(
        settings=Settings(),
        store=store,
        bus=EventBus(),
        ingestor=_DummyIngestor(),
        crop_analyzers=[],
        zone_store=zone_store,
    )


def _obs() -> PersonObservation:
    # foot point = ((10+50)/2, 90) / (100,100) = (0.3, 0.9) → inside the full-frame square
    return PersonObservation(camera="front", track_id="t1", crop=None, box=(10, 10, 50, 90), frame_size=(100, 100))


def test_ignore_zone_masks_detection(tmp_path):
    zs = ZoneStore(tmp_path / "z.json")
    zs.add(Zone(camera="front", name="street", kind="ignore", points=SQUARE))

    pipeline = _pipeline(zs, ProfileStore(":memory:"))

    assert pipeline._masked_by_ignore_zone(_obs()) is True


def test_ignore_zone_elsewhere_does_not_mask(tmp_path):
    zs = ZoneStore(tmp_path / "z.json")
    zs.add(Zone(camera="front", name="corner", kind="ignore", points=[(0.0, 0.0), (0.1, 0.0), (0.1, 0.1), (0.0, 0.1)]))

    pipeline = _pipeline(zs, ProfileStore(":memory:"))

    assert pipeline._masked_by_ignore_zone(_obs()) is False


def test_alert_zone_emits_once_within_cooldown(tmp_path):
    zs = ZoneStore(tmp_path / "z.json")
    zs.add(Zone(camera="front", name="gate", kind="alert", points=SQUARE))
    store = ProfileStore(":memory:")
    pipeline = _pipeline(zs, store)

    pipeline._emit_zone_alerts(_obs(), "person1")
    pipeline._emit_zone_alerts(_obs(), "person1")  # within cooldown → suppressed

    zone_events = [e for e in store.recent_events() if e["kind"] == "zone"]
    assert len(zone_events) == 1
    assert zone_events[0]["label"] == "gate"
