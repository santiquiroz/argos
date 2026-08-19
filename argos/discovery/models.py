"""Discovery result types + RTSP URL construction (pure, testable)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Credential:
    user: str
    password: str

    def masked(self) -> str:
        return f"{self.user}:{'*' * len(self.password) if self.password else '(blank)'}"


@dataclass(slots=True)
class DiscoveredCamera:
    ip: str
    vendor: str = "unknown"          # "hikvision" | "onvif" | "unknown"
    model: str | None = None
    channels: int = 1                # number of video channels (a DVR/NVR has several)
    onvif_url: str | None = None
    reachable_http: bool = False
    reachable_rtsp: bool = False
    # Credential audit outcome:
    default_credential: Credential | None = None   # a default cred that WORKED (insecure!)
    credential_checked: bool = False

    @property
    def insecure(self) -> bool:
        """True if a well-known default credential was accepted."""
        return self.default_credential is not None

    def rtsp_urls(self, *, substream: bool = True) -> list[str]:
        """Ready-to-use RTSP URLs per channel, using the working credential when known."""
        return [rtsp_url(self.ip, ch, substream=substream, credential=self.default_credential)
                for ch in range(1, self.channels + 1)]


def rtsp_url(ip: str, channel: int, *, substream: bool = True, credential: Credential | None = None, port: int = 554) -> str:
    """Hikvision/HiLook RTSP URL. ``<C>01`` = main stream, ``<C>02`` = sub stream."""
    stream = "02" if substream else "01"
    auth = f"{credential.user}:{credential.password}@" if credential else ""
    return f"rtsp://{auth}{ip}:{port}/Streaming/Channels/{channel}{stream}"
