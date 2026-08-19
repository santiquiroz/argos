import numpy as np

from argos.analyzers.base import Embedding
from argos.profiling.identity import _decide_person
from argos.profiling.store import Match, ProfileStore


def _unit(*values: float) -> np.ndarray:
    vec = np.array(values, dtype=np.float32)
    return vec / np.linalg.norm(vec)


def test_store_matches_same_modality_by_cosine():
    store = ProfileStore(":memory:")
    person = store.create_person()
    store.add_embedding(person_id=person, observation_id="o1", modality="reid", vector=_unit(1, 0, 0), ts=100.0)

    match = store.match_embedding("reid", _unit(0.99, 0.1, 0.0), min_score=0.5)

    assert match is not None
    assert match.person_id == person
    assert match.score > 0.9


def test_store_respects_since_ts_window():
    store = ProfileStore(":memory:")
    person = store.create_person()
    store.add_embedding(person_id=person, observation_id="o1", modality="reid", vector=_unit(1, 0, 0), ts=100.0)

    # A window that starts after the stored embedding excludes it.
    match = store.match_embedding("reid", _unit(1, 0, 0), min_score=0.5, since_ts=200.0)

    assert match is None


def test_enroll_marks_person():
    store = ProfileStore(":memory:")
    person = store.create_person()

    store.enroll(person, "Alice")

    row = next(p for p in store.list_persons() if p["id"] == person)
    assert row["name"] == "Alice"
    assert row["enrolled"] == 1


def test_events_roundtrip():
    store = ProfileStore(":memory:")

    store.add_event(person_id=None, camera="front", kind="behavior", label="loitering", score=0.8)

    events = store.recent_events()
    assert events[0]["kind"] == "behavior"
    assert events[0]["label"] == "loitering"


def test_fusion_priority_face_wins():
    matches = {
        "face": Match(person_id="P_face", modality="face", score=0.6),
        "reid": Match(person_id="P_reid", modality="reid", score=0.9),
    }

    assert _decide_person(matches).person_id == "P_face"


def test_fusion_gait_and_reid_agreement():
    same = {
        "gait": Match(person_id="P", modality="gait", score=0.6),
        "reid": Match(person_id="P", modality="reid", score=0.7),
    }
    disagree = {
        "gait": Match(person_id="P1", modality="gait", score=0.6),
        "reid": Match(person_id="P2", modality="reid", score=0.7),
    }

    assert _decide_person(same).person_id == "P"
    # On disagreement, gait (more robust) wins over re-ID.
    assert _decide_person(disagree).person_id == "P1"


def test_fusion_no_match_returns_none():
    assert _decide_person({}) is None
