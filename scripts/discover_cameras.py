#!/usr/bin/env python3
"""Discover cameras on YOUR local network and audit them for default credentials.

Scans your local subnet (ONVIF WS-Discovery + a TCP sweep), identifies Hikvision/HiLook devices,
checks whether any still accept well-known default passwords, and prints ready-to-use RTSP URLs.

This is a self-audit of devices you own/administer. Do not run it against networks you are not
authorised to test.

Usage:
    python scripts/discover_cameras.py
    python scripts/discover_cameras.py --subnet 192.168.1.0/24
    python scripts/discover_cameras.py --no-audit          # identify only, no credential probe
    python scripts/discover_cameras.py --ip 192.168.1.64   # also probe a specific IP
    python scripts/discover_cameras.py --json

Requires: pip install httpx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from argos.discovery import scan_network  # noqa: E402
from argos.discovery.models import DiscoveredCamera  # noqa: E402


def _row(cam: DiscoveredCamera) -> str:
    sec = "[!] DEFAULT CREDS" if cam.insecure else ("secure" if cam.credential_checked else "-")
    model = (cam.model or cam.vendor)[:22]
    return f"{cam.ip:<15} {model:<22} ch={cam.channels:<2} http={_yn(cam.reachable_http)} rtsp={_yn(cam.reachable_rtsp)}  {sec}"


def _yn(value: bool) -> str:
    return "Y" if value else "n"


def _print_report(cameras: list[DiscoveredCamera]) -> None:
    if not cameras:
        print("No cameras found. Check that the DVR/cameras are powered, on this subnet, and that "
              "ONVIF/RTSP is enabled. Try --subnet or --ip to target explicitly.")
        return
    print(f"\nFound {len(cameras)} device(s):\n")
    print(f"{'IP':<15} {'MODEL/VENDOR':<22} {'CH':<5} {'HTTP':<6} {'RTSP':<6} SECURITY")
    print("-" * 78)
    for cam in cameras:
        print(_row(cam))

    insecure = [c for c in cameras if c.insecure]
    if insecure:
        print("\n[!] These devices accept a DEFAULT password - change it in the DVR/camera web UI:")
        for cam in insecure:
            print(f"   {cam.ip}  ({cam.default_credential.masked()})")

    print("\nSuggested RTSP URLs (sub-stream, for ARGOS_RTSP_CAMERAS):")
    for cam in cameras:
        for i, url in enumerate(cam.rtsp_urls(substream=True), start=1):
            print(f"   {cam.ip} ch{i}: {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subnet", help="CIDR to scan (default: auto-detected local /24)")
    parser.add_argument("--ip", action="append", default=[], help="also probe this IP (repeatable)")
    parser.add_argument("--no-sweep", action="store_true", help="ONVIF discovery only, skip TCP sweep")
    parser.add_argument("--no-audit", action="store_true", help="identify only, do not test credentials")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    print("Scanning your local network for cameras... (this audits devices you own)")
    cameras = scan_network(
        subnet=args.subnet,
        do_sweep=not args.no_sweep,
        extra_ips=tuple(args.ip),
        audit_credentials=not args.no_audit,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps([_as_dict(c) for c in cameras], indent=2))
    else:
        _print_report(cameras)
    return 0


def _as_dict(cam: DiscoveredCamera) -> dict:
    return {
        "ip": cam.ip,
        "vendor": cam.vendor,
        "model": cam.model,
        "channels": cam.channels,
        "reachable_http": cam.reachable_http,
        "reachable_rtsp": cam.reachable_rtsp,
        "insecure_default_credential": cam.default_credential.masked() if cam.insecure else None,
        "rtsp_urls": cam.rtsp_urls(substream=True),
    }


if __name__ == "__main__":
    raise SystemExit(main())
