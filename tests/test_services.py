"""Service-dispatch tests — mock the device layer to verify end-to-end service → device."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant

from custom_components.led_controller.const import DOMAIN
from custom_components.led_controller.coordinator import LedControllerCoordinator
from custom_components.led_controller.services import (
    SERVICE_CLEAR_LED,
    SERVICE_SET_LED,
    async_register_services,
)


def _fake_coordinator(hass: HomeAssistant, device_id: str = "dev-1", led_count: int = 5):
    coord = MagicMock(spec=LedControllerCoordinator)
    coord.device = MagicMock()
    coord.device.led_count = led_count
    coord.device.model = "zen32"
    coord.device.supports_hsv = False
    coord.device.supported_palette = frozenset(
        ["red", "green", "blue", "white", "cyan", "yellow", "magenta"]
    )
    coord.device.set_led = AsyncMock()
    coord.device.clear_led = AsyncMock()
    coord.entry = MagicMock()
    coord.entry.data = {"device_id": device_id}
    coord.record_write = MagicMock()
    return coord


async def test_set_led_dispatches_to_device(hass: HomeAssistant):
    coord = _fake_coordinator(hass)
    hass.data[DOMAIN] = {"entry-1": coord}

    async_register_services(hass)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_LED,
        {"device_id": "dev-1", "led": 1, "color": "red", "brightness": 50},
        blocking=True,
    )

    assert coord.device.set_led.await_count == 1
    args = coord.device.set_led.await_args
    assert args.args[1] == 1  # led_idx
    assert args.args[3] == 50  # brightness_pct


async def test_set_led_all_expands(hass: HomeAssistant):
    coord = _fake_coordinator(hass, led_count=3)
    hass.data[DOMAIN] = {"entry-1": coord}

    async_register_services(hass)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_LED,
        {"device_id": "dev-1", "led": "all", "color": "blue"},
        blocking=True,
    )
    assert coord.device.set_led.await_count == 3


async def test_clear_led(hass: HomeAssistant):
    coord = _fake_coordinator(hass)
    hass.data[DOMAIN] = {"entry-1": coord}

    async_register_services(hass)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CLEAR_LED,
        {"device_id": "dev-1", "led": 2},
        blocking=True,
    )
    assert coord.device.clear_led.await_count == 1
