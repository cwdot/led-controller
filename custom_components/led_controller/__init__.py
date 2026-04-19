"""LED Controller integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_FRIENDLY_NAME,
    CONF_LED_COUNT,
    CONF_Z2M_BASE_TOPIC,
    CONF_Z2M_NAME,
    DEVICE_TYPE_LED_COUNT,
    DEVICE_TYPE_VZM35,
    DOMAIN,
)
from .coordinator import LedControllerCoordinator
from .devices import build_device
from .services import async_register_services, async_unregister_services

PLATFORMS: list[Platform] = [Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = {**entry.data, **entry.options}
    device_type = data[CONF_DEVICE_TYPE]
    device_id = data[CONF_DEVICE_ID]
    led_count = data.get(CONF_LED_COUNT, DEVICE_TYPE_LED_COUNT[device_type])
    friendly = data.get(CONF_FRIENDLY_NAME) or device_id

    extra_kwargs: dict = {}
    if device_type == DEVICE_TYPE_VZM35:
        extra_kwargs["z2m_name"] = data.get(CONF_Z2M_NAME)
        extra_kwargs["z2m_base_topic"] = data.get(CONF_Z2M_BASE_TOPIC)
    device = build_device(device_type, device_id, led_count=led_count, **extra_kwargs)
    coordinator = LedControllerCoordinator(hass, entry, device, friendly)
    # First refresh is best-effort; Inovelli devices have no meaningful readback,
    # so we don't hard-fail if it can't produce data yet.
    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            async_unregister_services(hass)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
