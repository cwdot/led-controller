"""Per-device coordinator — polls LED state and caches writes for entity readback."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .devices import LedDevice, LedState

_LOGGER = logging.getLogger(__name__)

_DEFAULT_INTERVAL = timedelta(minutes=10)


class LedControllerCoordinator(DataUpdateCoordinator[dict[int, LedState]]):
    """Polls LED state at a safety-net interval. Service calls update cache directly."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device: LedDevice,
        friendly_name: str,
    ) -> None:
        self.entry = entry
        self.device = device
        self.friendly_name = friendly_name
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{entry.entry_id}",
            update_interval=_DEFAULT_INTERVAL,
        )

    async def _async_update_data(self) -> dict[int, LedState]:
        try:
            state = await self.device.read_all(self.hass)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"read_all failed: {err}") from err
        merged = dict(self.data or {})
        merged.update(state)
        return merged

    def record_write(self, led_idx: int, state: LedState) -> None:
        """Update cached state after a successful service call without re-polling."""
        merged = dict(self.data or {})
        merged[led_idx] = state
        self.async_set_updated_data(merged)
