"""End-to-end integration setup tests — verify entities are actually registered."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.led_controller.const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_FRIENDLY_NAME,
    CONF_Z2M_NAME,
    DEVICE_TYPE_VZM35,
    DEVICE_TYPE_ZEN32,
    DOMAIN,
)


async def test_zen32_setup_registers_5_light_entities(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DEVICE_TYPE_ZEN32}:abc",
        data={
            CONF_DEVICE_TYPE: DEVICE_TYPE_ZEN32,
            CONF_DEVICE_ID: "abc",
            CONF_FRIENDLY_NAME: "Master Scene Wall",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    registry = er.async_get(hass)
    entities = [e for e in registry.entities.values() if e.config_entry_id == entry.entry_id]
    assert len(entities) == 5, f"expected 5 LED entities, got {[e.entity_id for e in entities]}"
    assert any("relay" in (e.original_name or "").lower() for e in entities)


async def test_vzm35_setup_registers_7_light_entities(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DEVICE_TYPE_VZM35}:xyz",
        data={
            CONF_DEVICE_TYPE: DEVICE_TYPE_VZM35,
            CONF_DEVICE_ID: "xyz",
            CONF_FRIENDLY_NAME: "Bedroom Fan",
            CONF_Z2M_NAME: "bedroom_fan",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    registry = er.async_get(hass)
    entities = [e for e in registry.entities.values() if e.config_entry_id == entry.entry_id]
    assert len(entities) == 7
