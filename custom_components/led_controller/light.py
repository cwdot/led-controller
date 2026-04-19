"""Light platform — one LightEntity per LED per device."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .color import Hsv, parse_color
from .const import DOMAIN
from .coordinator import LedControllerCoordinator
from .devices import LedState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LedControllerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        LedControllerLight(coordinator, entry, led_idx)
        for led_idx in range(1, coordinator.device.led_count + 1)
    )


class LedControllerLight(CoordinatorEntity[LedControllerCoordinator], LightEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LedControllerCoordinator,
        entry: ConfigEntry,
        led_idx: int,
    ) -> None:
        super().__init__(coordinator)
        self._led_idx = led_idx
        self._attr_unique_id = f"{entry.entry_id}_led_{led_idx}"
        self._attr_name = f"LED {led_idx}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=coordinator.friendly_name,
            manufacturer="LED Controller",
            model=coordinator.device.model,
        )
        if coordinator.device.supports_hsv:
            self._attr_supported_color_modes = {ColorMode.HS}
            self._attr_color_mode = ColorMode.HS
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

    @property
    def _state(self) -> LedState | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get(self._led_idx)

    @property
    def is_on(self) -> bool:
        state = self._state
        return bool(state and state.on)

    @property
    def brightness(self) -> int | None:
        state = self._state
        if not state or state.brightness_pct is None:
            return None
        return int(round(state.brightness_pct * 255 / 100))

    @property
    def hs_color(self) -> tuple[float, float] | None:
        state = self._state
        if not state or state.color is None:
            return None
        return (state.color.h, state.color.s * 100)

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness_pct = 100
        if ATTR_BRIGHTNESS in kwargs:
            brightness_pct = int(round(kwargs[ATTR_BRIGHTNESS] / 255 * 100))
        if ATTR_HS_COLOR in kwargs:
            h, s = kwargs[ATTR_HS_COLOR]
            color = Hsv(h=float(h), s=float(s) / 100.0, v=brightness_pct / 100.0)
        else:
            existing = self._state.color if self._state else None
            color = existing or parse_color("white")
        await self.coordinator.device.set_led(self.hass, self._led_idx, color, brightness_pct)
        self.coordinator.record_write(
            self._led_idx,
            LedState(on=True, color=color, brightness_pct=brightness_pct),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.device.clear_led(self.hass, self._led_idx)
        self.coordinator.record_write(self._led_idx, LedState(on=False))
