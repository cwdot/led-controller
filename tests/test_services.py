"""Service-dispatch tests — mock the device layer to verify end-to-end service → device."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
    # ZEN32 has no bulk write; remove the auto-created mock attr so the service falls
    # back to per-LED writes (getattr(..., "set_all", None) -> None).
    del coord.device.set_all
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


async def test_set_led_all_uses_bulk_when_available(hass: HomeAssistant):
    coord = _fake_coordinator(hass, led_count=4)
    coord.device.supports_hsv = True  # Inovelli-style device
    coord.device.set_all = AsyncMock()
    hass.data[DOMAIN] = {"entry-1": coord}

    async_register_services(hass)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_LED,
        {"device_id": "dev-1", "led": "all", "color": "blue", "brightness": 70},
        blocking=True,
    )

    # One bulk write, no per-LED writes, but every LED's cache is still recorded.
    assert coord.device.set_all.await_count == 1
    assert coord.device.set_led.await_count == 0
    assert coord.record_write.call_count == 4


async def test_set_led_rejects_bool_selector(hass: HomeAssistant):
    coord = _fake_coordinator(hass)
    hass.data[DOMAIN] = {"entry-1": coord}

    async_register_services(hass)
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_LED,
            {"device_id": "dev-1", "led": True, "color": "red"},
            blocking=True,
        )


async def test_set_led_targets_by_entity_id(hass: HomeAssistant):
    # entity_id targeting must resolve to the owning device_id and dispatch.
    owner = MockConfigEntry(domain="zwave_js")
    owner.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=owner.entry_id, identifiers={("zwave_js", "node-1")}
    )
    ent_reg = er.async_get(hass)
    entity = ent_reg.async_get_or_create(
        "light", "led_controller", "uniq-1", config_entry=owner, device_id=device.id
    )

    coord = _fake_coordinator(hass, device_id=device.id)
    hass.data[DOMAIN] = {"entry-1": coord}

    async_register_services(hass)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_LED,
        {"entity_id": entity.entity_id, "led": 1, "color": "red"},
        blocking=True,
    )
    assert coord.device.set_led.await_count == 1


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
