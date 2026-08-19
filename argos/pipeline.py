"""The orchestrator: ingest → analyzers (admission-gated) → identity fusion → events.

Owns the per-track temporal buffers that the action/gait analyzers need, applies per-analyzer enable
flags, persists observations/embeddings, and publishes events to the bus for the SSE endpoint.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque

import cv2
import numpy as np

from argos.analyzers.action import ActionAnalyzer, ActionResult
from argos.analyzers.base import Analyzer, Embedding
from argos.config import Settings
from argos.core.devices import AdmissionGate, make_probe
from argos.events import EventBus
from argos.ingest.base import Ingestor, PersonObservation
from argos.logging import get_logger
from argos.notify import Notifier
from argos.profiling.identity import IdentityResolver
from argos.profiling.store import ProfileStore

log = get_logger(__name__)

_POSE_WINDOW = 30
_ACTION_MIN_SCORE = 0.6
_BEHAVIOR_LABELS = {"falling", "running", "loitering", "climbing", "fighting"}


class Pipeline:
    def __init__(
        self,
        *,
        settings: Settings,
        store: ProfileStore,
        bus: EventBus,
        ingestor: Ingestor,
        crop_analyzers: list[Analyzer],
        action_analyzer: ActionAnalyzer | None = None,
        notifier: Notifier | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._bus = bus
        self._ingestor = ingestor
        self._crop_analyzers = crop_analyzers
        self._action_analyzer = action_analyzer
        self._notifier = notifier
        self._resolver = IdentityResolver(store)
        self._gate = AdmissionGate(
            concurrency=settings.gpu_concurrency,
            min_free_mb=settings.min_free_vram_mb,
            probe=make_probe(settings.device),
        )
        self._pose_buffers: dict[str, deque] = defaultdict(lambda: deque(maxlen=_POSE_WINDOW))
        self._stopped = False

    async def run(self) -> None:
        log.info("pipeline_start", ingest=self._settings.ingest, analyzers=[a.name for a in self._crop_analyzers])
        try:
            async for obs in self._ingestor.observations():
                if self._stopped:
                    break
                await self._process(obs)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # keep the loop resilient; one bad frame shouldn't kill ingest
            log.error("pipeline_error", error=str(exc))

    async def stop(self) -> None:
        self._stopped = True
        await self._ingestor.close()
        if self._notifier is not None:
            await self._notifier.close()

    async def _process(self, obs: PersonObservation) -> None:
        async with self._gate:
            results = await asyncio.to_thread(self._run_crop_analyzers, obs.crop)
        embeddings = [r.embedding for r in results if r.embedding is not None]
        self._buffer_pose(obs.track_id, results)
        decision = self._resolver.resolve(embeddings, obs.timestamp)
        self._persist(obs, embeddings, decision.person_id)
        self._emit_identity(obs, decision)
        await self._maybe_emit_behavior(obs, decision.person_id)

    def _run_crop_analyzers(self, crop: np.ndarray | None) -> list:
        if crop is None:
            return []
        results = []
        for analyzer in self._crop_analyzers:
            result = analyzer.analyze(crop)
            if result is not None:
                results.append(result)
        return results

    def _buffer_pose(self, track_id: str, results: list) -> None:
        for result in results:
            if result.analyzer == "pose" and result.keypoints is not None:
                self._pose_buffers[track_id].append(result.keypoints)

    def _persist(self, obs: PersonObservation, embeddings: list[Embedding], person_id: str) -> None:
        crop_path = self._save_crop(obs)
        self._store.add_observation(
            observation_id=obs.observation_id,
            person_id=person_id,
            camera=obs.camera,
            track_id=obs.track_id,
            ts=obs.timestamp,
            crop_path=crop_path,
        )
        for emb in embeddings:
            self._store.add_embedding(
                person_id=person_id,
                observation_id=obs.observation_id,
                modality=emb.modality,
                vector=emb.vector,
                ts=obs.timestamp,
            )
        self._store.touch_person(person_id)

    def _save_crop(self, obs: PersonObservation) -> str | None:
        if obs.crop is None:
            return None
        path = self._settings.crops_dir() / f"{obs.observation_id}.jpg"
        cv2.imwrite(str(path), cv2.cvtColor(obs.crop, cv2.COLOR_RGB2BGR))
        return str(path)

    def _emit_identity(self, obs: PersonObservation, decision) -> None:
        kind = "new_person" if decision.is_new else "recognized"
        event = self._store.add_event(
            person_id=decision.person_id, camera=obs.camera, kind=kind, label=None, score=None
        )
        self._publish(event)

    async def _maybe_emit_behavior(self, obs: PersonObservation, person_id: str) -> None:
        if self._action_analyzer is None or not self._action_analyzer.available:
            return
        buffer = self._pose_buffers.get(obs.track_id)
        if not buffer or len(buffer) < 2:
            return
        result: ActionResult | None = await asyncio.to_thread(
            self._action_analyzer.analyze_sequence, list(buffer)
        )
        if result is None or result.label not in _BEHAVIOR_LABELS or result.score < _ACTION_MIN_SCORE:
            return
        event = self._store.add_event(
            person_id=person_id, camera=obs.camera, kind="behavior", label=result.label, score=result.score
        )
        self._publish(event)
        log.info("behavior_detected", label=result.label, score=round(result.score, 3), camera=obs.camera)

    def _publish(self, event: dict) -> None:
        self._bus.publish(event)
        if self._notifier is not None:
            self._notifier.dispatch(event)
