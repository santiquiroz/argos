"""The ingest contract shared by every source.

An ``Ingestor`` yields ``PersonObservation``s: one tracked person at one moment, as a cropped image
plus metadata. Analyzers and profiling depend only on this dataclass, so they are ingest-agnostic.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class PersonObservation:
    """One tracked person, seen once.

    ``crop`` is the person region (RGB HxWx3 uint8). ``frame`` is the full frame when available
    (needed for silhouette-based gait). ``track_id`` is stable for the life of a track within a
    single ingest source, so temporal analyzers can window on it.
    """

    camera: str
    track_id: str
    crop: np.ndarray | None
    timestamp: float = field(default_factory=time.time)
    observation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    box: tuple[int, int, int, int] | None = None  # x1, y1, x2, y2 in the full frame
    frame: np.ndarray | None = None
    label: str = "person"
    score: float | None = None


class Ingestor(ABC):
    """Async source of person observations."""

    @abstractmethod
    def observations(self) -> AsyncIterator[PersonObservation]:
        """Yield observations until the source is exhausted or ``close`` is called."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Release the source (sockets, subprocesses, MQTT connection)."""
        raise NotImplementedError
