"""Tests for Zen32Device: verifies correct zwave_js.set_config_parameter calls."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.led_controller.color import parse_color
from custom_components.led_controller.const import (
    ZEN32_COLOR_VALUES,
    ZEN32_MODE_ALWAYS_OFF,
    ZEN32_MODE_ALWAYS_ON,
)
from custom_components.led_controller.devices.zen32 import Zen32Device


def _mock_hass() -> object:
    class _Services:
        def __init__(self) -> None:
            self.async_call = AsyncMock(return_value=None)

    class _Hass:
        def __init__(self) -> None:
            self.services = _Services()

    return _Hass()


async def test_set_led_scene_button_issues_three_calls():
    hass = _mock_hass()
    device = Zen32Device(device_id="dev-123")

    await device.set_led(hass, 1, parse_color("red"), 100)

    assert hass.services.async_call.await_count == 3
    calls = [c.args for c in hass.services.async_call.await_args_list]
    # Button 1 mode param = 2; color param = 7; brightness param = 12.
    assert calls[0][1] == "set_config_parameter"
    assert calls[0][2]["parameter"] == 2
    assert calls[0][2]["value"] == ZEN32_MODE_ALWAYS_ON
    assert calls[1][2]["parameter"] == 7
    assert calls[1][2]["value"] == ZEN32_COLOR_VALUES["red"]
    assert calls[2][2]["parameter"] == 12
    assert calls[2][2]["value"] == 0  # bright


async def test_set_led_relay_uses_correct_params():
    hass = _mock_hass()
    device = Zen32Device(device_id="dev-123")

    await device.set_led(hass, 5, parse_color("cyan"), 50)

    calls = [c.args for c in hass.services.async_call.await_args_list]
    # Relay (led_idx=5): mode=6, color=11, brightness=16.
    assert calls[0][2]["parameter"] == 6
    assert calls[1][2]["parameter"] == 11
    assert calls[1][2]["value"] == ZEN32_COLOR_VALUES["cyan"]
    assert calls[2][2]["parameter"] == 16
    assert calls[2][2]["value"] == 1  # medium


async def test_clear_led_sets_mode_always_off():
    hass = _mock_hass()
    device = Zen32Device(device_id="dev-123")

    await device.clear_led(hass, 3)

    assert hass.services.async_call.await_count == 1
    call = hass.services.async_call.await_args_list[0]
    # Button 3 mode = param 4.
    assert call.args[2]["parameter"] == 4
    assert call.args[2]["value"] == ZEN32_MODE_ALWAYS_OFF


async def test_invalid_led_rejected():
    hass = _mock_hass()
    device = Zen32Device(device_id="dev-123")

    with pytest.raises(ValueError):
        await device.set_led(hass, 6, parse_color("red"), 100)
    with pytest.raises(ValueError):
        await device.set_led(hass, 0, parse_color("red"), 100)
