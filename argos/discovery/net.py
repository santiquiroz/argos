"""Low-level network helpers for discovery: local subnet + TCP liveness sweep."""

from __future__ import annotations

import concurrent.futures
import ipaddress
import socket

from argos.logging import get_logger

log = get_logger(__name__)


def local_ipv4() -> str | None:
    """Best-effort local IPv4 (no traffic sent — just picks the default-route interface)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def local_subnet() -> str | None:
    """The /24 the host sits on, e.g. ``192.168.1.0/24``."""
    ip = local_ipv4()
    if ip is None:
        return None
    return str(ipaddress.ip_network(f"{ip}/24", strict=False))


def _tcp_open(ip: str, port: int, timeout: float) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((ip, port)) == 0


def sweep(subnet: str, *, ports: tuple[int, ...] = (554, 80, 8000), timeout: float = 0.4, workers: int = 128) -> set[str]:
    """Return IPs in ``subnet`` with any of ``ports`` open. Concurrent, short-timeout."""
    hosts = [str(h) for h in ipaddress.ip_network(subnet, strict=False).hosts()]
    alive: set[str] = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_any_port_open, ip, ports, timeout): ip for ip in hosts}
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                alive.add(futures[future])
    log.info("subnet_sweep_done", subnet=subnet, alive=len(alive))
    return alive


def _any_port_open(ip: str, ports: tuple[int, ...], timeout: float) -> bool:
    return any(_tcp_open(ip, port, timeout) for port in ports)
