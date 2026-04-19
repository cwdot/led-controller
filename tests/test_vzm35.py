"""Tests for Vzm35Device: verifies zha.issue_zigbee_cluster_command shape."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.led_controller.color import parse_color
from custom_components.led_controller.const import (
    VZM35_CLUSTER_ID,
    VZM35_CMD_INDIVIDUAL_LED_EFFECT,
    VZM35_CMD_LED_EFFECT,
    VZM35_DURATION_INDEFINITE,
    VZM35_EFFECT_OFF,
    VZM35_EFFECT_SOLID,
)
from custom_components.led_controller.devices.vzm35 import Vzm35Device


def _mock_hass() -> object:
    class _Services:
        def __init__(self) -> None:
            self.async_call = AsyncMock(return_value=None)

    class _Hass:
        def __init__(self) -> None:
            self.services = _Services()

    return _Hass()


def _registry_entry_with_ieee(ieee: str):
    entry = MagicMock()
    entry.identifiers = {("zha", ieee)}
    entry.connections = set()
    return entry


@pytest.fixture
def patched_registry():
    entry = _registry_entry_with_ieee("00:11:22:33:44:55:66:77")
    with patch(
        "custom_components.led_controller.devices.vzm35.async_get_device_registry"
    ) as mocked:
        mocked.return_value.async_get.return_value = entry
        yield mocked


async def test_set_led_issues_individual_command(patched_registry):
    hass = _mock_hass()
    device = Vzm35Device(device_id="dev-zig")

    await device.set_led(hass, 3, parse_color("green"), 75)

    call = hass.services.async_call.await_args_list[0]
    assert call.args[1] == "issue_zigbee_cluster_command"
    payload = call.args[2]
    assert payload["cluster_id"] == VZM35_CLUSTER_ID
    assert payload["command"] == VZM35_CMD_INDIVIDUAL_LED_EFFECT
    assert payload["params"]["led_number"] == 3
    assert payload["params"]["led_effect"] == VZM35_EFFECT_SOLID
    assert payload["params"]["led_level"] == 75
    assert payload["params"]["led_duration"] == VZM35_DURATION_INDEFINITE


async def test_clear_led_uses_effect_off(patched_registry):
    hass = _mock_hass()
    device = Vzm35Device(device_id="dev-zig")

    await device.clear_led(hass, 2)

    call = hass.services.async_call.await_args_list[0]
    assert call.args[2]["params"]["led_effect"] == VZM35_EFFECT_OFF


async def test_set_all_uses_broadcast_command(patched_registry):
    hass = _mock_hass()
    device = Vzm35Device(device_id="dev-zig")

    await device.set_all(hass, parse_color("magenta"), 60)

    call = hass.services.async_call.await_args_list[0]
    assert call.args[2]["command"] == VZM35_CMD_LED_EFFECT
    assert call.args[2]["params"]["led_level"] == 60
