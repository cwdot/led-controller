"""Verify LightEntity advertises the right color modes per device type."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.components.light import ColorMode

from custom_components.led_controller.devices.vzm35 import Vzm35Device
from custom_components.led_controller.devices.zen32 import Zen32Device
from custom_components.led_controller.light import LedControllerLight


def _fake_coordinator(device) -> MagicMock:
    coord = MagicMock()
    coord.device = device
    coord.friendly_name = "Test"
    coord.data = {}
    return coord


def test_inovelli_light_exposes_hs_color_mode():
    device = Vzm35Device(device_id="dev", z2m_name="fan")
    coord = _fake_coordinator(device)
    entry = MagicMock()
    entry.entry_id = "e1"

    light = LedControllerLight(coord, entry, led_idx=1)

    assert ColorMode.HS in light.supported_color_modes
    assert light.color_mode == ColorMode.HS


def test_zen32_light_exposes_onoff_only():
    device = Zen32Device(device_id="dev")
    coord = _fake_coordinator(device)
    entry = MagicMock()
    entry.entry_id = "e1"

    light = LedControllerLight(coord, entry, led_idx=1)

    assert light.supported_color_modes == {ColorMode.ONOFF}
