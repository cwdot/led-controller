"""Tests for Vzw32Device: verifies packed-value encoding and correct param routing."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.led_controller.color import parse_color
from custom_components.led_controller.const import (
    VZW32_DURATION_INDEFINITE,
    VZW32_EFFECT_OFF,
    VZW32_EFFECT_SOLID,
    VZW32_PARAM_ALL,
    VZW32_PARAM_PER_LED,
)
from custom_components.led_controller.devices.vzw32 import Vzw32Device, _pack


def _mock_hass() -> object:
    class _Services:
        def __init__(self) -> None:
            self.async_call = AsyncMock(return_value=None)

    class _Hass:
        def __init__(self) -> None:
            self.services = _Services()

    return _Hass()


def test_pack_layout():
    # effect=1, duration=255, level=50, color=100 → 0x01FF3264
    assert _pack(1, 255, 50, 100) == (1 << 24) | (255 << 16) | (50 << 8) | 100


async def test_set_led_writes_to_correct_param():
    hass = _mock_hass()
    device = Vzw32Device(device_id="dev-abc")

    await device.set_led(hass, 1, parse_color("red"), 100)

    call = hass.services.async_call.await_args_list[0]
    assert call.args[1] == "set_config_parameter"
    assert call.args[2]["parameter"] == VZW32_PARAM_PER_LED[1]
    packed = call.args[2]["value"]
    assert (packed >> 24) & 0xFF == VZW32_EFFECT_SOLID
    assert (packed >> 16) & 0xFF == VZW32_DURATION_INDEFINITE
    assert (packed >> 8) & 0xFF == 100  # brightness


async def test_clear_led_sends_effect_off():
    hass = _mock_hass()
    device = Vzw32Device(device_id="dev-abc")

    await device.clear_led(hass, 2)

    call = hass.services.async_call.await_args_list[0]
    assert call.args[2]["parameter"] == VZW32_PARAM_PER_LED[2]
    assert (call.args[2]["value"] >> 24) & 0xFF == VZW32_EFFECT_OFF


async def test_set_all_uses_param_99():
    hass = _mock_hass()
    device = Vzw32Device(device_id="dev-abc")

    await device.set_all(hass, parse_color("blue"), 80)

    call = hass.services.async_call.await_args_list[0]
    assert call.args[2]["parameter"] == VZW32_PARAM_ALL


async def test_out_of_range_led_rejected():
    hass = _mock_hass()
    device = Vzw32Device(device_id="dev-abc")
    with pytest.raises(ValueError):
        await device.set_led(hass, 5, parse_color("red"), 100)
