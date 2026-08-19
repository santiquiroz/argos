"""Hikvision/HiLook identification + credential self-audit over ISAPI (HTTP Digest).

For each candidate IP we hit ``/ISAPI/System/deviceInfo``. An unauthenticated 401 that looks like a
Hikvision device tells us the vendor; a 200 with one of the default credentials tells us the device
is **insecure** (and gives us its model + channel count for building RTSP URLs).
"""

from __future__ import annotations

import re

import httpx

from argos.discovery.models import Credential, DiscoveredCamera
from argos.logging import get_logger

log = get_logger(__name__)

_HTTP_PORTS = (80, 8000)
_HIK_HINT = re.compile(r"hikvision|/ISAPI/|IP ?Camera|DVR|NVR", re.IGNORECASE)


def _tag(xml: str, name: str) -> str | None:
    """Namespace-agnostic single-tag text extract."""
    match = re.search(rf"<(?:\w+:)?{name}>([^<]+)</(?:\w+:)?{name}>", xml)
    return match.group(1).strip() if match else None


def parse_device_info(xml: str) -> dict[str, str | None]:
    return {
        "name": _tag(xml, "deviceName"),
        "model": _tag(xml, "model"),
        "serial": _tag(xml, "serialNumber"),
        "firmware": _tag(xml, "firmwareVersion"),
    }


def parse_channel_count(xml: str) -> int:
    """Count video input channels from an ISAPI channel-list response (>=1)."""
    # Match open, self-closing, or attributed tags: <X>, <X/>, <X attr=...>.
    count = len(re.findall(r"<(?:\w+:)?VideoInputChannel[\s/>]", xml))
    if count == 0:
        count = len(re.findall(r"<(?:\w+:)?StreamingChannel[\s/>]", xml))
    return max(count, 1)


def _looks_hikvision(response: httpx.Response) -> bool:
    server = response.headers.get("server", "")
    auth = response.headers.get("www-authenticate", "")
    return bool(_HIK_HINT.search(server) or _HIK_HINT.search(auth) or _HIK_HINT.search(response.text[:512]))


def _get(url: str, timeout: float, credential: Credential | None = None) -> httpx.Response | None:
    auth = httpx.DigestAuth(credential.user, credential.password) if credential else None
    try:
        return httpx.get(url, auth=auth, timeout=timeout)
    except httpx.HTTPError:
        return None


def _channel_count(base: str, credential: Credential, timeout: float) -> int:
    for path in ("/ISAPI/System/Video/inputs/channels", "/ISAPI/Streaming/channels"):
        resp = _get(f"{base}{path}", timeout, credential)
        if resp is not None and resp.status_code == 200:
            return parse_channel_count(resp.text)
    return 1


def audit_ip(ip: str, credentials: tuple[Credential, ...], *, timeout: float = 3.0) -> DiscoveredCamera | None:
    """Identify + credential-audit one IP over ISAPI. ``None`` if no HTTP device answered."""
    for port in _HTTP_PORTS:
        base = f"http://{ip}:{port}"
        probe = _get(f"{base}/ISAPI/System/deviceInfo", timeout)
        if probe is None:
            continue
        cam = DiscoveredCamera(ip=ip, reachable_http=True)
        if _looks_hikvision(probe):
            cam.vendor = "hikvision"
        _try_credentials(cam, base, credentials, timeout)
        return cam
    return None


def _try_credentials(cam: DiscoveredCamera, base: str, credentials: tuple[Credential, ...], timeout: float) -> None:
    for cred in credentials:
        resp = _get(f"{base}/ISAPI/System/deviceInfo", timeout, cred)
        if resp is not None and resp.status_code == 200:
            info = parse_device_info(resp.text)
            cam.vendor = "hikvision"
            cam.model = info["model"] or info["name"]
            cam.default_credential = cred
            cam.channels = _channel_count(base, cred, timeout)
            cam.credential_checked = True
            log.warning("insecure_default_credential", ip=cam.ip, cred=cred.masked(), model=cam.model)
            return
    cam.credential_checked = True
