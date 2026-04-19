"""Coordinator merge semantics — a transient read must not clobber known state."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant

from custom_components.led_controller.coordinator import LedControllerCoordinator
from custom_components.led_controller.devices import LedState


async def test_transient_read_failure_preserves_cached_state(hass: HomeAssistant) -> None:
    # read_all omits LED 2 (its read failed); the merge must keep LED 2's prior value.
    device = MagicMock()
    device.read_all = AsyncMock(return_value={1: LedState(on=True, brightness_pct=100)})
    entry = MagicMock()
    entry.entry_id = "entry-1"

    coord = LedControllerCoordinator(hass, entry, device, "Friendly")
    coord.async_set_updated_data(
        {
            1: LedState(on=False),
            2: LedState(on=True, brightness_pct=80),
        }
    )

    merged = await coord._async_update_data()

    assert merged[1].on is True and merged[1].brightness_pct == 100  # refreshed
    assert merged[2].on is True and merged[2].brightness_pct == 80  # preserved
