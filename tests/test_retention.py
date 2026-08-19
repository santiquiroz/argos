import os
import time

from argos.retention import purge_crop_files


def test_purge_removes_only_old_crops(tmp_path):
    fresh = tmp_path / "fresh.jpg"
    old = tmp_path / "old.jpg"
    fresh.write_bytes(b"x")
    old.write_bytes(b"x")
    # Backdate `old` to 20 days ago.
    twenty_days = time.time() - 20 * 86400
    os.utime(old, (twenty_days, twenty_days))

    removed = purge_crop_files(tmp_path, days=14)

    assert removed == 1
    assert fresh.exists()
    assert not old.exists()


def test_purge_ignores_non_jpg(tmp_path):
    (tmp_path / "keep.txt").write_bytes(b"x")

    assert purge_crop_files(tmp_path, days=0) == 0
    assert (tmp_path / "keep.txt").exists()
