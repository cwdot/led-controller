"""Inovelli VZM35-SN Blue Series fan switch (zigbee via ZHA, 7 LEDs).

Protocol reference:
- zigpy/zha-device-handlers, zhaquirks/inovelli/__init__.py (InovelliCluster).
- Cluster 0xFC31 (64561), endpoint 1.
- Command 0x01 led_effect(effect, color, level, duration) — all LEDs.
- Command 0x03 individual_led_effect(led, effect, color, level, duration) — single LED.
- effect=1 "solid", duration=255 indefinite.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from ..color import Hsv, to_inovelli_hue, to_inovelli_level
from ..const import (
    DEVICE_TYPE_LED_COUNT,
    DEVICE_TYPE_VZM35,
    VZM35_CLUSTER_ID,
    VZM35_CMD_INDIVIDUAL_LED_EFFECT,
    VZM35_CMD_LED_EFFECT,
    VZM35_DURATION_INDEFINITE,
    VZM35_EFFECT_OFF,
    VZM35_EFFECT_SOLID,
    VZM35_ENDPOINT_ID,
    ZHA_INTEGRATION,
)
from .base import LedDevice, LedState

_LOGGER = logging.getLogger(__name__)


class Vzm35Device(LedDevice):
    model = DEVICE_TYPE_VZM35
    supported_palette = frozenset(
        ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta", "pink", "white"]
    )
    supports_hsv = True

    def __init__(self, device_id: str, led_count: int | None = None) -> None:
        super().__init__(device_id)
        self.led_count = led_count or DEVICE_TYPE_LED_COUNT[DEVICE_TYPE_VZM35]
        self._cache: dict[int, LedState] = {}

    async def set_led(
        self,
        hass: HomeAssistant,
        led_idx: int,
        color: Hsv,
        brightness_pct: int,
        mode: str | None = None,
        transition: int | None = None,
    ) -> None:
        self.validate_led(led_idx)
        ieee = _resolve_ieee(hass, self.device_id)
        hue = to_inovelli_hue(color)
        level = max(0, min(100, brightness_pct))
        await self._issue_command(
            hass,
            ieee,
            VZM35_CMD_INDIVIDUAL_LED_EFFECT,
            {
                "led_number": led_idx,
                "led_effect": VZM35_EFFECT_SOLID,
                "led_color": hue,
                "led_level": level,
                "led_duration": VZM35_DURATION_INDEFINITE,
            },
        )
        self._cache[led_idx] = LedState(on=True, color=color, brightness_pct=level, mode=mode)

    async def clear_led(self, hass: HomeAssistant, led_idx: int) -> None:
        self.validate_led(led_idx)
        ieee = _resolve_ieee(hass, self.device_id)
        await self._issue_command(
            hass,
            ieee,
            VZM35_CMD_INDIVIDUAL_LED_EFFECT,
            {
                "led_number": led_idx,
                "led_effect": VZM35_EFFECT_OFF,
                "led_color": 0,
                "led_level": 0,
                "led_duration": 0,
            },
        )
        self._cache[led_idx] = LedState(on=False)

    async def set_all(self, hass: HomeAssistant, color: Hsv, brightness_pct: int) -> None:
        ieee = _resolve_ieee(hass, self.device_id)
        hue = to_inovelli_hue(color)
        if brightness_pct is None:
            level = to_inovelli_level(color)
        else:
            level = max(0, min(100, brightness_pct))
        await self._issue_command(
            hass,
            ieee,
            VZM35_CMD_LED_EFFECT,
            {
                "led_effect": VZM35_EFFECT_SOLID,
                "led_color": hue,
                "led_level": level,
                "led_duration": VZM35_DURATION_INDEFINITE,
            },
        )
        for led_idx in range(1, self.led_count + 1):
            self._cache[led_idx] = LedState(on=True, color=color, brightness_pct=level)

    async def read_all(self, hass: HomeAssistant) -> dict[int, LedState]:
        # ZHA doesn't expose readback for the led_effect commands; return cache.
        return dict(self._cache)

    async def _issue_command(
        self,
        hass: HomeAssistant,
        ieee: str,
        command: int,
        params: dict[str, object],
    ) -> None:
        await hass.services.async_call(
            ZHA_INTEGRATION,
            "issue_zigbee_cluster_command",
            {
                "ieee": ieee,
                "endpoint_id": VZM35_ENDPOINT_ID,
                "cluster_id": VZM35_CLUSTER_ID,
                "cluster_type": "in",
                "command": command,
                "command_type": "server",
                "params": params,
            },
            blocking=True,
        )


def _resolve_ieee(hass: HomeAssistant, device_id: str) -> str:
    """Look up the IEEE address of a ZHA device from the device registry."""
    registry = async_get_device_registry(hass)
    entry = registry.async_get(device_id)
    if entry is None:
        raise ValueError(f"device_id {device_id!r} not found in registry")
    for domain, identifier in entry.identifiers:
        if domain == ZHA_INTEGRATION:
            # ZHA identifiers are tuples ("zha", ieee) — identifier is the IEEE string.
            return identifier
    for connection_type, value in entry.connections:
        if connection_type == "zigbee":
            return value
    raise ValueError(f"device_id {device_id!r} is not a ZHA device")
