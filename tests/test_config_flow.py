"""Config flow tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
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


def _mock_device_entry():
    entry = MagicMock()
    entry.name = "Kitchen ZEN32"
    entry.name_by_user = None
    entry.config_entries = {"zwave-entry-id"}
    entry.identifiers = set()
    return entry


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    with (
        patch("custom_components.led_controller.config_flow.dr.async_get") as mock_dr,
        patch(
            "custom_components.led_controller.config_flow._integration_entry_ids",
            return_value={"zwave-entry-id"},
        ),
        patch("custom_components.led_controller.async_setup_entry", return_value=True),
    ):
        mock_dr.return_value.async_get.return_value = _mock_device_entry()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_DEVICE_TYPE: DEVICE_TYPE_ZEN32}
        )
        assert result2["step_id"] == "device"

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_DEVICE_ID: "device-abc", CONF_FRIENDLY_NAME: "Kitchen"},
        )
        await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["title"] == "Kitchen"
    assert result3["data"][CONF_DEVICE_TYPE] == DEVICE_TYPE_ZEN32
    assert result3["data"][CONF_DEVICE_ID] == "device-abc"


async def test_duplicate_device_aborts(hass: HomeAssistant) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DEVICE_TYPE_ZEN32}:device-abc",
        data={CONF_DEVICE_TYPE: DEVICE_TYPE_ZEN32, CONF_DEVICE_ID: "device-abc"},
    ).add_to_hass(hass)

    with (
        patch("custom_components.led_controller.config_flow.dr.async_get") as mock_dr,
        patch(
            "custom_components.led_controller.config_flow._integration_entry_ids",
            return_value={"zwave-entry-id"},
        ),
    ):
        mock_dr.return_value.async_get.return_value = _mock_device_entry()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_DEVICE_TYPE: DEVICE_TYPE_ZEN32}
        )
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_DEVICE_ID: "device-abc", CONF_FRIENDLY_NAME: "Kitchen"},
        )

    assert result3["type"] == FlowResultType.ABORT
    assert result3["reason"] == "already_configured"


async def test_wrong_integration_shows_error(hass: HomeAssistant) -> None:
    with (
        patch("custom_components.led_controller.config_flow.dr.async_get") as mock_dr,
        patch(
            "custom_components.led_controller.config_flow._integration_entry_ids",
            return_value={"some-other-entry"},
        ),
    ):
        entry = _mock_device_entry()
        entry.config_entries = {"not-zwave-entry"}
        mock_dr.return_value.async_get.return_value = entry

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_DEVICE_TYPE: DEVICE_TYPE_ZEN32}
        )
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_DEVICE_ID: "device-abc", CONF_FRIENDLY_NAME: "Kitchen"},
        )

    assert result3["type"] == FlowResultType.FORM
    assert result3["errors"] == {CONF_DEVICE_ID: "wrong_integration"}


async def test_vzm35_requires_z2m_name(hass: HomeAssistant) -> None:
    with (
        patch("custom_components.led_controller.config_flow.dr.async_get") as mock_dr,
        patch(
            "custom_components.led_controller.config_flow._integration_entry_ids",
            return_value={"mqtt-entry-id"},
        ),
        patch("custom_components.led_controller.async_setup_entry", return_value=True),
    ):
        entry = _mock_device_entry()
        entry.config_entries = {"mqtt-entry-id"}
        mock_dr.return_value.async_get.return_value = entry

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_DEVICE_TYPE: DEVICE_TYPE_VZM35}
        )
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_DEVICE_ID: "mqtt-device",
                CONF_FRIENDLY_NAME: "Bedroom Fan",
                CONF_Z2M_NAME: "bedroom_fan",
            },
        )
        await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["data"][CONF_Z2M_NAME] == "bedroom_fan"
