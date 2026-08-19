"""Explainable, conservative identity fusion.

Face, re-ID and gait embeddings live in different spaces, so we match each modality independently
(cosine within its own space) and combine the matches with a transparent priority rule rather than
concatenating vectors or training a linker (see ARCHITECTURE.md, assumption A2).

Priority (strongest evidence first):
  1. face                       → assign (high precision when a face is visible)
  2. gait AND re-ID agree       → assign (two independent signals concur)
  3. gait                       → assign (survives clothing change / low face res)
  4. re-ID within time window   → assign tentatively (same outfit, recent)
  5. otherwise                  → new tentative person

The bias is toward creating a new identity over a wrong merge; merges/splits are surfaced for human
review in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from argos.analyzers.base import Embedding
from argos.profiling.store import Match, ProfileStore

# Per-modality cosine thresholds. Tune against your data; conservative defaults.
FACE_THRESHOLD = 0.42
GAIT_THRESHOLD = 0.50
REID_THRESHOLD = 0.55
# re-ID only links within this window (seconds) — clothing changes across days.
REID_WINDOW_S = 6 * 3600


@dataclass(frozen=True, slots=True)
class IdentityDecision:
    person_id: str
    is_new: bool
    evidence: list[Match] = field(default_factory=list)


def _match_for(store: ProfileStore, emb: Embedding, *, threshold: float, since_ts: float | None) -> Match | None:
    return store.match_embedding(emb.modality, emb.vector, min_score=threshold, since_ts=since_ts)


def _collect_matches(store: ProfileStore, embeddings: list[Embedding], now: float) -> dict[str, Match]:
    """Best match per modality, keyed by modality."""
    matches: dict[str, Match] = {}
    for emb in embeddings:
        if emb.modality == "face":
            m = _match_for(store, emb, threshold=FACE_THRESHOLD, since_ts=None)
        elif emb.modality == "gait":
            m = _match_for(store, emb, threshold=GAIT_THRESHOLD, since_ts=None)
        elif emb.modality == "reid":
            m = _match_for(store, emb, threshold=REID_THRESHOLD, since_ts=now - REID_WINDOW_S)
        else:
            m = None
        if m is not None:
            matches[emb.modality] = m
    return matches


def _decide_person(matches: dict[str, Match]) -> Match | None:
    """Apply the priority rule. Returns the winning match or ``None`` (→ new person)."""
    if "face" in matches:
        return matches["face"]
    gait, reid = matches.get("gait"), matches.get("reid")
    if gait and reid and gait.person_id == reid.person_id:
        return gait
    if gait:
        return gait
    if reid:
        return reid
    return None


class IdentityResolver:
    def __init__(self, store: ProfileStore) -> None:
        self._store = store

    def resolve(self, embeddings: list[Embedding], now: float) -> IdentityDecision:
        matches = _collect_matches(self._store, embeddings, now)
        winner = _decide_person(matches)
        if winner is not None:
            return IdentityDecision(person_id=winner.person_id, is_new=False, evidence=list(matches.values()))
        person_id = self._store.create_person()
        return IdentityDecision(person_id=person_id, is_new=True, evidence=[])
