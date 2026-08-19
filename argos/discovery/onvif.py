"""ONVIF WS-Discovery — find cameras/NVRs that announce themselves via UDP multicast.

Sends a WS-Discovery Probe to 239.255.255.250:3702 and collects the ProbeMatch responses. No auth,
no writes; purely a "who's an ONVIF device on this LAN?" broadcast.
"""

from __future__ import annotations

import re
import socket
import uuid

from argos.logging import get_logger

log = get_logger(__name__)

_MCAST_ADDR = "239.255.255.250"
_MCAST_PORT = 3702
_IP_IN_URL = re.compile(r"https?://(\d{1,3}(?:\.\d{1,3}){3})")


def _probe_message() -> bytes:
    message_id = f"uuid:{uuid.uuid4()}"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"'
        ' xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"'
        ' xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"'
        ' xmlns:dn="http://www.onvif.org/ver10/network/wsdl">'
        f"<e:Header><w:MessageID>{message_id}</w:MessageID>"
        "<w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>"
        "<w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action></e:Header>"
        "<e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body>"
        "</e:Envelope>"
    ).encode("utf-8")


def parse_xaddr_ips(payload: str) -> set[str]:
    """Extract device IPs from a ProbeMatch response's XAddrs URLs."""
    return set(_IP_IN_URL.findall(payload))


def ws_discovery(*, timeout: float = 3.0) -> dict[str, str]:
    """Return ``{ip: service_url}`` for ONVIF devices that answer the probe."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(timeout)
    found: dict[str, str] = {}
    try:
        sock.sendto(_probe_message(), (_MCAST_ADDR, _MCAST_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                break
            payload = data.decode("utf-8", errors="ignore")
            for ip in parse_xaddr_ips(payload) or {addr[0]}:
                found.setdefault(ip, _first_url(payload))
    except OSError as exc:
        log.warning("ws_discovery_error", error=str(exc))
    finally:
        sock.close()
    log.info("ws_discovery_done", devices=len(found))
    return found


def _first_url(payload: str) -> str:
    match = re.search(r"https?://[^\s<]+", payload)
    return match.group(0) if match else ""
