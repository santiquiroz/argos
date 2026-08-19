#!/usr/bin/env python3
"""Export a YOLO person detector to ONNX for the direct-RTSP path.

Produces ``<models_dir>/detector.onnx`` (default models/weights/). Uses Ultralytics, which downloads
the chosen checkpoint on first run.

Usage:
    pip install ultralytics
    python scripts/export_yolo.py                 # yolov8n -> models/weights/detector.onnx
    python scripts/export_yolo.py --model yolov8s --imgsz 640

Note: Ultralytics YOLO is AGPL-3.0 — compatible with this project, but verify for your use.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DIR = _ROOT / "models" / "weights"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="yolov8n", help="Ultralytics model name or .pt path")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--opset", type=int, default=12)
    parser.add_argument("--models-dir", type=Path, default=_DEFAULT_DIR)
    parser.add_argument("--out", default="detector.onnx")
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError:
        print("ultralytics not installed. Run: pip install ultralytics", file=sys.stderr)
        return 1

    print(f"Exporting {args.model} to ONNX (imgsz={args.imgsz}, opset={args.opset})…")
    exported = YOLO(f"{args.model}.pt").export(format="onnx", imgsz=args.imgsz, opset=args.opset)

    args.models_dir.mkdir(parents=True, exist_ok=True)
    target = args.models_dir / args.out
    shutil.move(str(exported), target)
    print(f"Done: {target.resolve()}")
    print("Set ARGOS_INGEST=rtsp and ARGOS_RTSP_CAMERAS in .env, then `python -m argos`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
