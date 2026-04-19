"""Inovelli VZW32-SN Red Series mmWave dimmer (z-wave, 4 LEDs).

Protocol reference:
- Inovelli Help Center, Red Series Presence Dimmer mmWave Parameters.
- Per-LED notification params (64/69/74/79) use a packed 32-bit value:
    value = (effect << 24) | (duration << 16) | (level << 8) | color
  with effect=1 → solid on, duration=255 → indefinite.
- Param 99 drives all LEDs at once.
- Defaults (params 95-98) set the always-on color/intensity when the load is on/off.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..color import Hsv, to_inovelli_hue, to_inovelli_level
from ..const import (
    DEVICE_TYPE_LED_COUNT,
    DEVICE_TYPE_VZW32,
    VZW32_DURATION_INDEFINITE,
    VZW32_EFFECT_OFF,
    VZW32_EFFECT_SOLID,
    VZW32_PARAM_ALL,
    VZW32_PARAM_PER_LED,
    ZWAVE_INTEGRATION,
)
from .base import LedDevice, LedState

_LOGGER = logging.getLogger(__name__)


class Vzw32Device(LedDevice):
    model = DEVICE_TYPE_VZW32
    supported_palette = frozenset(
        ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta", "pink", "white"]
    )
    supports_hsv = True

    def __init__(self, device_id: str, led_count: int | None = None) -> None:
        super().__init__(device_id)
        self.led_count = led_count or DEVICE_TYPE_LED_COUNT[DEVICE_TYPE_VZW32]
        # Readback from notification params isn't reliable on Inovelli; cache last writes.
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
        hue = to_inovelli_hue(color)
        level = to_inovelli_level(Hsv(color.h, color.s, max(color.v, brightness_pct / 100.0)))
        # Caller passes brightness_pct separately; let it override the HSV value channel.
        level = max(0, min(100, brightness_pct))
        packed = _pack(VZW32_EFFECT_SOLID, VZW32_DURATION_INDEFINITE, level, hue)
        await self._set_param(hass, VZW32_PARAM_PER_LED[led_idx], packed)
        self._cache[led_idx] = LedState(on=True, color=color, brightness_pct=level, mode=mode)

    async def clear_led(self, hass: HomeAssistant, led_idx: int) -> None:
        self.validate_led(led_idx)
        packed = _pack(VZW32_EFFECT_OFF, 0, 0, 0)
        await self._set_param(hass, VZW32_PARAM_PER_LED[led_idx], packed)
        self._cache[led_idx] = LedState(on=False)

    async def set_all(self, hass: HomeAssistant, color: Hsv, brightness_pct: int) -> None:
        """Drive all LEDs via param 99 — slightly faster than N sequential writes."""
        hue = to_inovelli_hue(color)
        level = max(0, min(100, brightness_pct))
        packed = _pack(VZW32_EFFECT_SOLID, VZW32_DURATION_INDEFINITE, level, hue)
        await self._set_param(hass, VZW32_PARAM_ALL, packed)
        for led_idx in range(1, self.led_count + 1):
            self._cache[led_idx] = LedState(on=True, color=color, brightness_pct=level)

    async def read_all(self, hass: HomeAssistant) -> dict[int, LedState]:
        # Inovelli notification params don't report meaningful readback; return cache.
        return dict(self._cache)

    async def _set_param(self, hass: HomeAssistant, parameter: int, value: int) -> None:
        await hass.services.async_call(
            ZWAVE_INTEGRATION,
            "set_config_parameter",
            {
                "device_id": self.device_id,
                "parameter": parameter,
                "value": value,
            },
            blocking=True,
        )


def _pack(effect: int, duration: int, level: int, color: int) -> int:
    """Encode an Inovelli notification-LED 32-bit value."""
    effect &= 0xFF
    duration &= 0xFF
    level &= 0xFF
    color &= 0xFF
    return (effect << 24) | (duration << 16) | (level << 8) | color
