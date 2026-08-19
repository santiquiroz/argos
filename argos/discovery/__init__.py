"""Camera discovery + credential self-audit for your own LAN.

Finds ONVIF/Hikvision/HiLook devices on your local network, checks whether any still accept
well-known **default** credentials (so you can fix the insecure ones), and produces ready-to-use
RTSP URLs.

Scope + ethics: this is an onboarding and *defensive* self-audit tool. It targets your own local
subnet by default and is meant to inventory and harden **devices you own or administer**. Do not
point it at networks or devices you are not authorised to test.
"""

from argos.discovery.models import DiscoveredCamera
from argos.discovery.scan import scan_network

__all__ = ["DiscoveredCamera", "scan_network"]
