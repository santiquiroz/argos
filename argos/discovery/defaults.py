"""Well-known default credentials for Hikvision/HiLook-class devices.

Used ONLY to audit your own cameras: if one of these still works, that camera is insecure and you
should change its password. This is a short, public, widely-documented list — not a brute-force
dictionary. Newer HiLook/Hikvision firmware forces a password on first boot (no default), which is
the secure behaviour this audit is checking for.
"""

from __future__ import annotations

from argos.discovery.models import Credential

# Ordered most-to-least common. Keep this list SHORT and public-knowledge only.
DEFAULT_CREDENTIALS: tuple[Credential, ...] = (
    Credential("admin", "12345"),
    Credential("admin", "admin"),
    Credential("admin", "123456"),
    Credential("admin", "888888"),
    Credential("admin", "password"),
    Credential("admin", "Admin12345"),
    Credential("admin", ""),
)
