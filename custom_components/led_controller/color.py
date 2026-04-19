"""Color normalization, palette snapping, and device-specific encoding."""

from __future__ import annotations

import colorsys
import logging
import re
from dataclasses import dataclass

from .const import CANONICAL_PALETTE, PALETTE_RGB, ZEN32_COLOR_VALUES

_LOGGER = logging.getLogger(__name__)

_HSV_RE = re.compile(r"^hsv:\s*(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\s*$", re.I)
_HEX_RE = re.compile(r"^#?([0-9a-f]{6})$", re.I)


@dataclass(frozen=True)
class Hsv:
    """Hue 0-360, saturation 0-1, value 0-1."""

    h: float
    s: float
    v: float


def parse_color(value: str) -> Hsv:
    """Parse canonical name, `hsv:H,S,V`, or `#RRGGBB` into HSV."""

    if not isinstance(value, str):
        raise ValueError(f"color must be a string, got {type(value).__name__}")
    stripped = value.strip().lower()

    name_rgb = PALETTE_RGB.get(stripped)
    if name_rgb is not None:
        return _rgb_to_hsv(*name_rgb)

    m = _HSV_RE.match(stripped)
    if m:
        h, s, v = (float(g) for g in m.groups())
        if not (0 <= h <= 360 and 0 <= s <= 1 and 0 <= v <= 1):
            raise ValueError(f"hsv out of range: {value!r}")
        return Hsv(h, s, v)

    m = _HEX_RE.match(stripped)
    if m:
        rgb = int(m.group(1), 16)
        return _rgb_to_hsv((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF)

    raise ValueError(f"unrecognized color: {value!r}")


def snap_to_palette(target: Hsv, palette: frozenset[str]) -> tuple[str, bool]:
    """Return (name, lost_fidelity) — nearest palette entry by HSV distance."""

    candidates = [name for name in CANONICAL_PALETTE if name in palette]
    if not candidates:
        raise ValueError("palette is empty")

    best_name = candidates[0]
    best_dist = float("inf")
    for name in candidates:
        candidate = _rgb_to_hsv(*PALETTE_RGB[name])
        dist = _hsv_distance(target, candidate)
        if dist < best_dist:
            best_dist = dist
            best_name = name

    # Fidelity is "lost" if the snap target differs from the canonical name for this hue.
    exact = _nearest_canonical_name(target)
    return best_name, best_name != exact


def to_inovelli_hue(target: Hsv) -> int:
    """Convert HSV hue 0-360 to Inovelli 0-255 hue scale."""

    # Inovelli wraps the 0-360 hue circle into 0-254; 255 is reserved for white (saturation 0).
    if target.s < 0.1:
        return 255
    return int(round(target.h / 360.0 * 254)) % 255


def to_inovelli_level(target: Hsv) -> int:
    """Convert HSV value 0-1 to Inovelli 0-100 intensity."""

    return max(0, min(100, int(round(target.v * 100))))


def to_zen32_color(target: Hsv) -> int:
    """Snap HSV to the 7-color ZEN32 palette and return its config value."""

    zen_palette = frozenset(ZEN32_COLOR_VALUES.keys())
    name, _ = snap_to_palette(target, zen_palette)
    return ZEN32_COLOR_VALUES[name]


def to_zen32_brightness(pct: int) -> int:
    """Map 0-100 brightness into ZEN32's 3-level enum (0=bright, 1=medium, 2=low)."""

    pct = max(0, min(100, pct))
    if pct >= 67:
        return 0
    if pct >= 34:
        return 1
    return 2


def hsv_to_rgb_hex(target: Hsv) -> str:
    r, g, b = colorsys.hsv_to_rgb(target.h / 360.0, target.s, target.v)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _rgb_to_hsv(r: int, g: int, b: int) -> Hsv:
    rh, rs, rv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return Hsv(rh * 360.0, rs, rv)


def _hsv_distance(a: Hsv, b: Hsv) -> float:
    # Weight hue more than value; saturation matters for white/color split.
    dh = min(abs(a.h - b.h), 360 - abs(a.h - b.h)) / 180.0
    ds = abs(a.s - b.s)
    dv = abs(a.v - b.v)
    return (dh * 2.0) ** 2 + ds**2 + dv**2


def _nearest_canonical_name(target: Hsv) -> str:
    best_name = CANONICAL_PALETTE[0]
    best_dist = float("inf")
    for name in CANONICAL_PALETTE:
        candidate = _rgb_to_hsv(*PALETTE_RGB[name])
        dist = _hsv_distance(target, candidate)
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name
