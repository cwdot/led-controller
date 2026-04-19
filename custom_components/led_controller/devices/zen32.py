"""Zooz ZEN32 scene controller (z-wave, 5 LEDs)."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..color import Hsv, to_zen32_brightness, to_zen32_color
from ..const import (
    DEVICE_TYPE_LED_COUNT,
    DEVICE_TYPE_ZEN32,
    ZEN32_BRIGHTNESS_BRIGHT,
    ZEN32_COLOR_VALUES,
    ZEN32_MODE_ALWAYS_OFF,
    ZEN32_MODE_ALWAYS_ON,
    ZEN32_MODE_LED_OFF_WHEN_ON,
    ZEN32_MODE_LED_ON_WHEN_ON,
    ZWAVE_INTEGRATION,
    zen32_brightness_param,
    zen32_color_param,
    zen32_mode_param,
)
from .base import LedDevice, LedState

_LOGGER = logging.getLogger(__name__)

_MODE_BY_NAME = {
    "on": ZEN32_MODE_LED_ON_WHEN_ON,
    "off": ZEN32_MODE_LED_OFF_WHEN_ON,
    "always_on": ZEN32_MODE_ALWAYS_ON,
    "always_off": ZEN32_MODE_ALWAYS_OFF,
}
_MODE_NAME_BY_VALUE = {v: k for k, v in _MODE_BY_NAME.items()}
_COLOR_NAME_BY_VALUE = {v: k for k, v in ZEN32_COLOR_VALUES.items()}


class Zen32Device(LedDevice):
    model = DEVICE_TYPE_ZEN32
    supported_palette = frozenset(ZEN32_COLOR_VALUES.keys())
    supports_hsv = False

    def __init__(self, device_id: str, led_count: int | None = None, **_extra: object) -> None:
        super().__init__(device_id)
        self.led_count = led_count or DEVICE_TYPE_LED_COUNT[DEVICE_TYPE_ZEN32]

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
        color_value = to_zen32_color(color)
        brightness_value = to_zen32_brightness(brightness_pct)
        mode_value = _MODE_BY_NAME.get(mode or "always_on", ZEN32_MODE_ALWAYS_ON)

        await self._set_param(hass, zen32_mode_param(led_idx), mode_value)
        await self._set_param(hass, zen32_color_param(led_idx), color_value)
        await self._set_param(hass, zen32_brightness_param(led_idx), brightness_value)

    async def clear_led(self, hass: HomeAssistant, led_idx: int) -> None:
        self.validate_led(led_idx)
        await self._set_param(hass, zen32_mode_param(led_idx), ZEN32_MODE_ALWAYS_OFF)

    async def read_all(self, hass: HomeAssistant) -> dict[int, LedState]:
        result: dict[int, LedState] = {}
        for led_idx in range(1, self.led_count + 1):
            try:
                mode = await self._get_param(hass, zen32_mode_param(led_idx))
                color = await self._get_param(hass, zen32_color_param(led_idx))
                brightness = await self._get_param(hass, zen32_brightness_param(led_idx))
            except Exception as err:  # noqa: BLE001 — readback is best-effort
                _LOGGER.debug("zen32 read failed led=%d: %s", led_idx, err)
                result[led_idx] = LedState()
                continue
            result[led_idx] = LedState(
                on=mode in (ZEN32_MODE_LED_ON_WHEN_ON, ZEN32_MODE_ALWAYS_ON),
                color=_hsv_for_zen32_color(color),
                brightness_pct=_pct_for_zen32_brightness(brightness),
                mode=_MODE_NAME_BY_VALUE.get(int(mode) if mode is not None else -1),
            )
        return result

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

    async def _get_param(self, hass: HomeAssistant, parameter: int) -> int | None:
        """Best-effort read via zwave_js.get_config_parameter (HA 2024.4+)."""
        response = await hass.services.async_call(
            ZWAVE_INTEGRATION,
            "get_config_parameter",
            {"device_id": self.device_id, "parameter": parameter},
            blocking=True,
            return_response=True,
        )
        if not response:
            return None
        # Response shape: {device_id: {parameter_name: {"value": N, ...}}}
        for _entity_id, params in response.items():
            for _name, entry in (params or {}).items():
                if isinstance(entry, dict) and "value" in entry:
                    return int(entry["value"])
        return None


def _hsv_for_zen32_color(value: int | None) -> Hsv | None:
    if value is None:
        return None
    name = _COLOR_NAME_BY_VALUE.get(int(value))
    if name is None:
        return None
    from ..color import parse_color  # local import to avoid cycle

    return parse_color(name)


def _pct_for_zen32_brightness(value: int | None) -> int | None:
    if value is None:
        return None
    return {0: 100, 1: 50, 2: 15}.get(int(value), ZEN32_BRIGHTNESS_BRIGHT)
