"""Inovelli VZM35-SN Blue Series fan switch via Zigbee2MQTT (7 LEDs).

Commands go through Home Assistant's `mqtt.publish` service with a JSON payload on
`<base_topic>/<friendly_name>/set`. Z2M exposes `individual_led_effect` (LEDs 1-7) and
`led_effect` (all LEDs) as composite features; we use `effect=solid` with
`duration=255` (indefinite) to drive a persistent color, and `effect=off` to clear.
"""

from __future__ import annotations

import json
import logging

from homeassistant.core import HomeAssistant

from ..color import Hsv, to_inovelli_hue, to_inovelli_level
from ..const import (
    DEFAULT_Z2M_BASE_TOPIC,
    DEVICE_TYPE_LED_COUNT,
    DEVICE_TYPE_VZM35,
    VZM35_DURATION_INDEFINITE,
    VZM35_EFFECT_OFF,
    VZM35_EFFECT_SOLID,
)
from .base import LedDevice, LedState

_LOGGER = logging.getLogger(__name__)


class Vzm35Device(LedDevice):
    model = DEVICE_TYPE_VZM35
    supported_palette = frozenset(
        ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta", "pink", "white"]
    )
    supports_hsv = True

    def __init__(
        self,
        device_id: str,
        led_count: int | None = None,
        z2m_name: str | None = None,
        z2m_base_topic: str | None = None,
        **_extra: object,
    ) -> None:
        super().__init__(device_id)
        self.led_count = led_count or DEVICE_TYPE_LED_COUNT[DEVICE_TYPE_VZM35]
        if not z2m_name:
            raise ValueError("VZM35 requires z2m_name (Zigbee2MQTT friendly name)")
        self.z2m_name = z2m_name
        self.base_topic = (z2m_base_topic or DEFAULT_Z2M_BASE_TOPIC).rstrip("/")
        self._cache: dict[int, LedState] = {}

    @property
    def set_topic(self) -> str:
        return f"{self.base_topic}/{self.z2m_name}/set"

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
        hue = to_inovelli_hue(color)
        level = max(0, min(100, brightness_pct))
        payload = {
            "individual_led_effect": {
                "led": led_idx,
                "effect": VZM35_EFFECT_SOLID,
                "color": hue,
                "level": level,
                "duration": VZM35_DURATION_INDEFINITE,
            }
        }
        await self._publish(hass, payload)
        self._cache[led_idx] = LedState(on=True, color=color, brightness_pct=level, mode=mode)

    async def clear_led(self, hass: HomeAssistant, led_idx: int) -> None:
        self.validate_led(led_idx)
        payload = {
            "individual_led_effect": {
                "led": led_idx,
                "effect": VZM35_EFFECT_OFF,
                "color": 0,
                "level": 0,
                "duration": 0,
            }
        }
        await self._publish(hass, payload)
        self._cache[led_idx] = LedState(on=False)

    async def set_all(self, hass: HomeAssistant, color: Hsv, brightness_pct: int) -> None:
        hue = to_inovelli_hue(color)
        if brightness_pct is None:
            level = to_inovelli_level(color)
        else:
            level = max(0, min(100, brightness_pct))
        payload = {
            "led_effect": {
                "effect": VZM35_EFFECT_SOLID,
                "color": hue,
                "level": level,
                "duration": VZM35_DURATION_INDEFINITE,
            }
        }
        await self._publish(hass, payload)
        for led_idx in range(1, self.led_count + 1):
            self._cache[led_idx] = LedState(on=True, color=color, brightness_pct=level)

    async def read_all(self, hass: HomeAssistant) -> dict[int, LedState]:
        # Z2M doesn't expose per-LED effect state on its reporting topics; return cache.
        return dict(self._cache)

    async def _publish(self, hass: HomeAssistant, payload: dict) -> None:
        await hass.services.async_call(
            "mqtt",
            "publish",
            {
                "topic": self.set_topic,
                "payload": json.dumps(payload),
                "qos": 0,
                "retain": False,
            },
            blocking=True,
        )
