"""Orchestrate discovery: ONVIF probe + LAN sweep → identify + credential-audit each device."""

from __future__ import annotations

import socket

from argos.discovery.defaults import DEFAULT_CREDENTIALS
from argos.discovery.hikvision import audit_ip
from argos.discovery.models import Credential, DiscoveredCamera
from argos.discovery.net import local_subnet, sweep
from argos.discovery.onvif import ws_discovery
from argos.logging import get_logger

log = get_logger(__name__)


def _rtsp_open(ip: str, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((ip, 554)) == 0


def _candidate_ips(subnet: str | None, do_sweep: bool, extra_ips: tuple[str, ...]) -> set[str]:
    ips: set[str] = set(ws_discovery().keys())
    if do_sweep:
        target = subnet or local_subnet()
        if target:
            ips |= sweep(target)
    ips |= set(extra_ips)
    return ips


def scan_network(
    *,
    subnet: str | None = None,
    do_sweep: bool = True,
    extra_ips: tuple[str, ...] = (),
    credentials: tuple[Credential, ...] = DEFAULT_CREDENTIALS,
    audit_credentials: bool = True,
    timeout: float = 3.0,
) -> list[DiscoveredCamera]:
    """Discover cameras on the LAN and (optionally) audit them for default credentials.

    ``audit_credentials=False`` skips the credential probe entirely (identification only).
    """
    creds = credentials if audit_credentials else ()
    ips = _candidate_ips(subnet, do_sweep, extra_ips)
    log.info("discovery_candidates", count=len(ips), audit=audit_credentials)
    cameras: list[DiscoveredCamera] = []
    for ip in sorted(ips, key=lambda a: tuple(int(o) for o in a.split("."))):
        cam = audit_ip(ip, creds, timeout=timeout)
        if cam is None:
            if not _rtsp_open(ip):
                continue
            cam = DiscoveredCamera(ip=ip)  # RTSP-only device, no ISAPI/HTTP
        cam.reachable_rtsp = _rtsp_open(ip)
        cameras.append(cam)
    log.info("discovery_done", cameras=len(cameras))
    return cameras
