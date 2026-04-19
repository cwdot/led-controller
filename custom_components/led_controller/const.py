"""Constants, device model identifiers, and protocol tables for led_controller."""

from __future__ import annotations

DOMAIN = "led_controller"

CONF_DEVICE_TYPE = "device_type"
CONF_DEVICE_ID = "device_id"
CONF_FRIENDLY_NAME = "friendly_name"
CONF_LED_COUNT = "led_count"
CONF_Z2M_NAME = "z2m_name"
CONF_Z2M_BASE_TOPIC = "z2m_base_topic"

DEFAULT_Z2M_BASE_TOPIC = "zigbee2mqtt"

DEVICE_TYPE_ZEN32 = "zen32"
DEVICE_TYPE_VZW32 = "vzw32"
DEVICE_TYPE_VZM35 = "vzm35"
DEVICE_TYPES = (DEVICE_TYPE_ZEN32, DEVICE_TYPE_VZW32, DEVICE_TYPE_VZM35)

# Z-wave / zigbee dispatch — which HA integration owns the device.
ZWAVE_INTEGRATION = "zwave_js"
ZHA_INTEGRATION = "zha"

MQTT_INTEGRATION = "mqtt"

DEVICE_TYPE_INTEGRATION = {
    DEVICE_TYPE_ZEN32: ZWAVE_INTEGRATION,
    DEVICE_TYPE_VZW32: ZWAVE_INTEGRATION,
    DEVICE_TYPE_VZM35: MQTT_INTEGRATION,
}

DEVICE_TYPE_LED_COUNT = {
    DEVICE_TYPE_ZEN32: 5,
    DEVICE_TYPE_VZW32: 4,
    DEVICE_TYPE_VZM35: 7,
}

# ---------------------------------------------------------------------------
# ZEN32 — Zooz scene controller
# ---------------------------------------------------------------------------
# User-facing LED numbering:
#   led_idx 1-4 = scene buttons (top of device, top-left → bottom-right)
#   led_idx 5   = relay button (large button at bottom)
#
# Zooz's z-wave config parameters put the relay LED first in each band:
#   mode:       param 1 (relay), params 2-5 (buttons 1-4)
#   color:      param 6 (relay), params 7-10 (buttons 1-4)
#   brightness: param 11 (relay), params 12-15 (buttons 1-4)


def _zen32_band_offset(led_idx: int) -> int:
    """Map led_idx (1-5 with 5=relay) to position within a Zooz param band (0=relay, 1-4=btns)."""
    if led_idx == 5:
        return 0
    return led_idx


def zen32_mode_param(led_idx: int) -> int:
    return _zen32_band_offset(led_idx) + 1


def zen32_color_param(led_idx: int) -> int:
    return _zen32_band_offset(led_idx) + 6


def zen32_brightness_param(led_idx: int) -> int:
    return _zen32_band_offset(led_idx) + 11


ZEN32_COLOR_VALUES: dict[str, int] = {
    "white": 0,
    "blue": 1,
    "green": 2,
    "red": 3,
    "magenta": 4,
    "yellow": 5,
    "cyan": 6,
}

ZEN32_BRIGHTNESS_BRIGHT = 0
ZEN32_BRIGHTNESS_MEDIUM = 1
ZEN32_BRIGHTNESS_LOW = 2

ZEN32_MODE_LED_OFF_WHEN_ON = 0
ZEN32_MODE_LED_ON_WHEN_ON = 1
ZEN32_MODE_ALWAYS_OFF = 2
ZEN32_MODE_ALWAYS_ON = 3

# ---------------------------------------------------------------------------
# VZW32-SN — Inovelli Red mmWave dimmer (z-wave 800-series)
#
# Source: Inovelli Help Center (Red Series Presence Dimmer mmWave Parameters).
# Per-LED notification params use a packed 32-bit value:
#   value = (effect << 24) | (duration << 16) | (brightness << 8) | color
# duration=255 → indefinite; effect=1 → solid on; effect=0 → off.
# ---------------------------------------------------------------------------
VZW32_PARAM_PER_LED: dict[int, int] = {
    1: 64,  # bottom LED
    2: 69,
    3: 74,
    4: 79,  # middle / top
}
VZW32_PARAM_ALL = 99  # all LEDs notification
VZW32_PARAM_DEFAULT_COLOR_ON = 95
VZW32_PARAM_DEFAULT_COLOR_OFF = 96
VZW32_PARAM_DEFAULT_INTENSITY_ON = 97
VZW32_PARAM_DEFAULT_INTENSITY_OFF = 98

VZW32_EFFECT_OFF = 0
VZW32_EFFECT_SOLID = 1
VZW32_DURATION_INDEFINITE = 255

# ---------------------------------------------------------------------------
# VZM35-SN — Inovelli Blue fan switch (zigbee via Zigbee2MQTT)
#
# Source: https://www.zigbee2mqtt.io/devices/VZM35-SN.html
# Commands go through mqtt.publish to `<base_topic>/<friendly_name>/set` with JSON.
#   {"individual_led_effect": {"led": 1..7, "effect": "solid"|"off"|..,
#                              "color": 0..255, "level": 0..100, "duration": 1..255}}
#   {"led_effect":            {"effect": ..., "color": ..., "level": ..., "duration": ...}}
# "solid" with duration=255 holds the color indefinitely.
# ---------------------------------------------------------------------------
VZM35_EFFECT_OFF = "off"
VZM35_EFFECT_SOLID = "solid"
VZM35_DURATION_INDEFINITE = 255

# ---------------------------------------------------------------------------
# Canonical palette shared across device types.
# Order matters only for HSV-distance snap stability.
# ---------------------------------------------------------------------------
CANONICAL_PALETTE: tuple[str, ...] = (
    "red",
    "orange",
    "yellow",
    "green",
    "cyan",
    "blue",
    "purple",
    "magenta",
    "pink",
    "white",
)

# RGB 0-255 for the canonical palette — used by snap + HSV conversion helpers.
PALETTE_RGB: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "orange": (255, 128, 0),
    "yellow": (255, 255, 0),
    "green": (0, 255, 0),
    "cyan": (0, 255, 255),
    "blue": (0, 0, 255),
    "purple": (128, 0, 255),
    "magenta": (255, 0, 255),
    "pink": (255, 128, 192),
    "white": (255, 255, 255),
}
