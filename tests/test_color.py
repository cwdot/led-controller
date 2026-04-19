"""Tests for color parsing, snapping, and device-specific encoders."""

from __future__ import annotations

import pytest

from custom_components.led_controller.color import (
    parse_color,
    snap_to_palette,
    to_inovelli_hue,
    to_zen32_brightness,
    to_zen32_color,
)
from custom_components.led_controller.const import ZEN32_COLOR_VALUES


def test_parse_name():
    hsv = parse_color("red")
    assert hsv.h >= 355 or hsv.h <= 5
    assert hsv.s > 0.95
    assert hsv.v > 0.95


def test_parse_hex():
    hsv = parse_color("#00ff00")
    assert 115 < hsv.h < 125
    assert hsv.s > 0.95


def test_parse_hsv():
    hsv = parse_color("hsv:240,1.0,0.5")
    assert hsv.h == 240
    assert hsv.s == 1.0
    assert hsv.v == 0.5


def test_parse_invalid():
    with pytest.raises(ValueError):
        parse_color("not-a-color")


def test_snap_zen32_purple_becomes_magenta():
    hsv = parse_color("purple")
    name, lost = snap_to_palette(hsv, frozenset(ZEN32_COLOR_VALUES.keys()))
    assert name in {"magenta", "blue"}
    # purple isn't in ZEN32 palette so fidelity is lost.
    assert lost is True


def test_snap_zen32_red_exact():
    hsv = parse_color("red")
    name, lost = snap_to_palette(hsv, frozenset(ZEN32_COLOR_VALUES.keys()))
    assert name == "red"
    assert lost is False


def test_to_zen32_color_returns_int():
    assert to_zen32_color(parse_color("red")) == ZEN32_COLOR_VALUES["red"]
    assert to_zen32_color(parse_color("cyan")) == ZEN32_COLOR_VALUES["cyan"]


def test_to_zen32_brightness_buckets():
    assert to_zen32_brightness(100) == 0
    assert to_zen32_brightness(70) == 0
    assert to_zen32_brightness(50) == 1
    assert to_zen32_brightness(20) == 2
    assert to_zen32_brightness(0) == 2


def test_to_inovelli_hue_red():
    # Red is hue 0 on both systems.
    assert to_inovelli_hue(parse_color("red")) in (0, 254)  # wraparound allowed


def test_to_inovelli_hue_white():
    # White has no saturation, Inovelli reserves 255 for white.
    assert to_inovelli_hue(parse_color("white")) == 255


def test_to_inovelli_hue_blue_midscale():
    # Blue is hue 240 → 240/360*254 ≈ 169.
    hue = to_inovelli_hue(parse_color("blue"))
    assert 165 <= hue <= 173
