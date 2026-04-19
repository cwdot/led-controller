"""Tests for Vzm35Device: verifies mqtt.publish payload shape for Zigbee2MQTT."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from custom_components.led_controller.color import parse_color
from custom_components.led_controller.const import (
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


def test_requires_z2m_name():
    with pytest.raises(ValueError):
        Vzm35Device(device_id="dev-zig")


async def test_set_led_publishes_individual_effect():
    hass = _mock_hass()
    device = Vzm35Device(device_id="dev-zig", z2m_name="bedroom_fan")

    await device.set_led(hass, 3, parse_color("green"), 75)

    call = hass.services.async_call.await_args_list[0]
    assert call.args[0] == "mqtt"
    assert call.args[1] == "publish"
    assert call.args[2]["topic"] == "zigbee2mqtt/bedroom_fan/set"
    payload = json.loads(call.args[2]["payload"])
    assert "individual_led_effect" in payload
    inner = payload["individual_led_effect"]
    assert inner["led"] == 3
    assert inner["effect"] == VZM35_EFFECT_SOLID
    assert inner["level"] == 75
    assert inner["duration"] == VZM35_DURATION_INDEFINITE


async def test_clear_led_sends_off_effect():
    hass = _mock_hass()
    device = Vzm35Device(device_id="dev-zig", z2m_name="bedroom_fan")

    await device.clear_led(hass, 2)

    payload = json.loads(hass.services.async_call.await_args_list[0].args[2]["payload"])
    assert payload["individual_led_effect"]["effect"] == VZM35_EFFECT_OFF


async def test_set_all_publishes_led_effect():
    hass = _mock_hass()
    device = Vzm35Device(device_id="dev-zig", z2m_name="bedroom_fan")

    await device.set_all(hass, parse_color("magenta"), 60)

    payload = json.loads(hass.services.async_call.await_args_list[0].args[2]["payload"])
    assert "led_effect" in payload
    assert payload["led_effect"]["level"] == 60


async def test_custom_base_topic():
    hass = _mock_hass()
    device = Vzm35Device(
        device_id="dev-zig",
        z2m_name="bedroom_fan",
        z2m_base_topic="custom/z2m",
    )

    await device.set_led(hass, 1, parse_color("red"), 100)

    call = hass.services.async_call.await_args_list[0]
    assert call.args[2]["topic"] == "custom/z2m/bedroom_fan/set"
