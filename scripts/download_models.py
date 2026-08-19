#!/usr/bin/env python3
"""Download analyzer models listed in models/registry.yaml.

Opt-in, per model. Verifies SHA-256 when the registry provides it. Models with ``url: null`` must be
obtained/exported manually — the script prints the instructions from the registry ``notes``.

Usage:
    python scripts/download_models.py --list
    python scripts/download_models.py pose reid face
    python scripts/download_models.py --all
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent
_REGISTRY = _ROOT / "models" / "registry.yaml"
_DEFAULT_DIR = _ROOT / "models" / "weights"


def load_registry() -> dict:
    with _REGISTRY.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["models"]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def print_catalog(models: dict, models_dir: Path) -> None:
    for name, spec in models.items():
        target = models_dir / spec["file"]
        status = "present" if target.is_file() else ("manual" if spec.get("url") is None else "available")
        print(f"[{status:9}] {name:8} {spec['file']:14} ~{spec.get('size_mb', '?')}MB  {spec['license']}")


def download_one(name: str, spec: dict, models_dir: Path) -> bool:
    target = models_dir / spec["file"]
    if target.is_file():
        print(f"  {name}: already present ({target})")
        return True
    url = spec.get("url")
    if not url:
        print(f"  {name}: manual step required —{spec.get('notes', '').strip()}")
        return False
    print(f"  {name}: downloading {url} …")
    models_dir.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, target)  # noqa: S310 - registry-controlled URL
    expected = spec.get("sha256")
    if expected:
        actual = sha256_of(target)
        if actual != expected:
            target.unlink(missing_ok=True)
            print(f"  {name}: SHA-256 mismatch (expected {expected}, got {actual}) — deleted", file=sys.stderr)
            return False
    else:
        print(f"  {name}: WARNING no sha256 in registry — integrity not verified")
    print(f"  {name}: done ({target})")
    return True


def main() -> int:
    models = load_registry()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="model tasks to download (e.g. pose reid face)")
    parser.add_argument("--list", action="store_true", help="show the catalog and exit")
    parser.add_argument("--all", action="store_true", help="download every model with a url")
    parser.add_argument("--models-dir", type=Path, default=_DEFAULT_DIR)
    args = parser.parse_args()

    if args.list or (not args.names and not args.all):
        print_catalog(models, args.models_dir)
        return 0

    selected = list(models) if args.all else args.names
    ok = True
    for name in selected:
        spec = models.get(name)
        if spec is None:
            print(f"  {name}: unknown model (see --list)", file=sys.stderr)
            ok = False
            continue
        ok &= download_one(name, spec, args.models_dir)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
