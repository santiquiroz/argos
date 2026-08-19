"""Data retention helpers (PRIVACY.md). DB rows are purged by ProfileStore; crop files here."""

from __future__ import annotations

import time
from pathlib import Path


def purge_crop_files(crops_dir: str | Path, days: int) -> int:
    """Delete crop JPEGs older than ``days`` (by mtime). Returns how many were removed."""
    cutoff = time.time() - days * 86400
    removed = 0
    for path in Path(crops_dir).glob("*.jpg"):
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed
