"""Persistence + per-modality embedding matching (SQLite).

Structured data (persons, observations, events, enrollments) and embeddings live in one SQLite
file. Matching is brute-force cosine within a modality (fast enough for a home deployment); the
``match_embedding`` interface hides that so a vector index (``sqlite-vec``/FAISS) can drop in later.

Retention limits (PRIVACY.md) are enforced by ``purge_expired``.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from argos.analyzers.preprocess import cosine_similarity
from argos.logging import get_logger

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS persons (
    id          TEXT PRIMARY KEY,
    name        TEXT,                 -- NULL until enrolled
    enrolled    INTEGER NOT NULL DEFAULT 0,
    created_at  REAL NOT NULL,
    last_seen   REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
    id          TEXT PRIMARY KEY,
    person_id   TEXT,
    camera      TEXT NOT NULL,
    track_id    TEXT NOT NULL,
    ts          REAL NOT NULL,
    crop_path   TEXT,
    FOREIGN KEY (person_id) REFERENCES persons(id)
);
CREATE TABLE IF NOT EXISTS embeddings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id      TEXT,
    observation_id TEXT,
    modality       TEXT NOT NULL,
    vector         BLOB NOT NULL,
    ts             REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id         TEXT PRIMARY KEY,
    person_id  TEXT,
    camera     TEXT,
    kind       TEXT NOT NULL,         -- 'new_person' | 'recognized' | 'behavior'
    label      TEXT,
    score      REAL,
    ts         REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_emb_modality ON embeddings(modality);
CREATE INDEX IF NOT EXISTS idx_obs_person ON observations(person_id);
CREATE INDEX IF NOT EXISTS idx_evt_ts ON events(ts);
"""


@dataclass(frozen=True, slots=True)
class Match:
    person_id: str
    modality: str
    score: float


def _to_blob(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def _from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


class ProfileStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # --- persons ---
    def create_person(self) -> str:
        person_id = uuid.uuid4().hex
        now = time.time()
        self._conn.execute(
            "INSERT INTO persons (id, name, enrolled, created_at, last_seen) VALUES (?, NULL, 0, ?, ?)",
            (person_id, now, now),
        )
        self._conn.commit()
        return person_id

    def touch_person(self, person_id: str) -> None:
        self._conn.execute("UPDATE persons SET last_seen = ? WHERE id = ?", (time.time(), person_id))
        self._conn.commit()

    def enroll(self, person_id: str, name: str) -> None:
        self._conn.execute(
            "UPDATE persons SET name = ?, enrolled = 1 WHERE id = ?", (name, person_id)
        )
        self._conn.commit()

    def list_persons(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, name, enrolled, created_at, last_seen FROM persons ORDER BY last_seen DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # --- observations / embeddings ---
    def add_observation(self, *, observation_id: str, person_id: str | None, camera: str, track_id: str, ts: float, crop_path: str | None) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO observations (id, person_id, camera, track_id, ts, crop_path) VALUES (?, ?, ?, ?, ?, ?)",
            (observation_id, person_id, camera, track_id, ts, crop_path),
        )
        self._conn.commit()

    def add_embedding(self, *, person_id: str | None, observation_id: str, modality: str, vector: np.ndarray, ts: float) -> None:
        self._conn.execute(
            "INSERT INTO embeddings (person_id, observation_id, modality, vector, ts) VALUES (?, ?, ?, ?, ?)",
            (person_id, observation_id, modality, _to_blob(vector), ts),
        )
        self._conn.commit()

    def match_embedding(self, modality: str, vector: np.ndarray, *, min_score: float, since_ts: float | None = None) -> Match | None:
        """Best person for this embedding within a modality, above ``min_score``.

        Brute-force cosine over stored embeddings of the same modality that already belong to a
        person. ``since_ts`` restricts re-ID-style matching to a recent window.
        """
        query = "SELECT person_id, vector FROM embeddings WHERE modality = ? AND person_id IS NOT NULL"
        params: list = [modality]
        if since_ts is not None:
            query += " AND ts >= ?"
            params.append(since_ts)
        best: Match | None = None
        for row in self._conn.execute(query, params):
            score = cosine_similarity(vector, _from_blob(row["vector"]))
            if score >= min_score and (best is None or score > best.score):
                best = Match(person_id=row["person_id"], modality=modality, score=score)
        return best

    # --- events ---
    def add_event(self, *, person_id: str | None, camera: str | None, kind: str, label: str | None, score: float | None) -> dict:
        event = {
            "id": uuid.uuid4().hex,
            "person_id": person_id,
            "camera": camera,
            "kind": kind,
            "label": label,
            "score": score,
            "ts": time.time(),
        }
        self._conn.execute(
            "INSERT INTO events (id, person_id, camera, kind, label, score, ts) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event["id"], person_id, camera, kind, label, score, event["ts"]),
        )
        self._conn.commit()
        return event

    def recent_events(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- retention ---
    def purge_expired(self, *, embeddings_days: int, events_days: int) -> None:
        now = time.time()
        emb_cutoff = now - embeddings_days * 86400
        evt_cutoff = now - events_days * 86400
        # Keep embeddings of enrolled persons; purge only un-enrolled/expired.
        self._conn.execute(
            """DELETE FROM embeddings WHERE ts < ? AND (person_id IS NULL OR person_id IN
               (SELECT id FROM persons WHERE enrolled = 0))""",
            (emb_cutoff,),
        )
        self._conn.execute("DELETE FROM events WHERE ts < ?", (evt_cutoff,))
        self._conn.commit()
        log.info("retention_purge", embeddings_days=embeddings_days, events_days=events_days)

    def close(self) -> None:
        self._conn.close()
