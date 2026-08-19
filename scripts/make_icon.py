#!/usr/bin/env python3
"""Generate the Argos app icon (aperture mark) as PNG + multi-size ICO. Run once.

    python scripts/make_icon.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

_ROOT = Path(__file__).resolve().parent.parent
_NAVY = (15, 23, 42, 255)       # #0F172A
_ACCENT = (56, 189, 248, 255)   # #38BDF8
_ACCENT2 = (14, 165, 233, 255)  # #0EA5E9
_SS = 4                          # supersample for anti-aliasing


def _rounded_bg(size: int, draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=_NAVY)


def _aperture(size: int, draw: ImageDraw.ImageDraw) -> None:
    cx = cy = size / 2
    r_out = size * 0.34
    r_in = size * 0.20
    ring_w = max(2, int(size * 0.035))
    # Outer ring.
    draw.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], outline=_ACCENT, width=ring_w)
    # Six aperture blades: chords of the inner iris, rotated to suggest an opening.
    blades = 6
    pts_in = [(cx + r_in * math.cos(math.radians(a)), cy + r_in * math.sin(math.radians(a)))
              for a in range(0, 360, 360 // blades)]
    draw.polygon(pts_in, outline=_ACCENT2, width=max(2, int(size * 0.025)))
    for i in range(blades):
        x1, y1 = pts_in[i]
        ang = math.radians(i * (360 / blades))
        x2 = cx + r_out * math.cos(ang + 0.55)
        y2 = cy + r_out * math.sin(ang + 0.55)
        draw.line([x1, y1, x2, y2], fill=_ACCENT, width=max(2, int(size * 0.02)))


def render(size: int) -> Image.Image:
    big = size * _SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _rounded_bg(big, draw)
    _aperture(big, draw)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    installer = _ROOT / "installer"
    installer.mkdir(exist_ok=True)
    render(256).save(installer / "argos.png")
    icon = render(256)
    icon.save(installer / "argos.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"wrote {installer / 'argos.png'} and {installer / 'argos.ico'}")


if __name__ == "__main__":
    main()
