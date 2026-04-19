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
    CONF_LED_COUNT,
    DEVICE_TYPE_ZEN32,
    DOMAIN,
)


def _mock_device_entry(integration: str = "zwave_js"):
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
        assert result["step_id"] == "user"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_DEVICE_TYPE: DEVICE_TYPE_ZEN32}
        )
        assert result2["type"] == FlowResultType.FORM
        assert result2["step_id"] == "device"

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_DEVICE_ID: "device-abc",
                CONF_FRIENDLY_NAME: "Kitchen",
                CONF_LED_COUNT: 5,
            },
        )
        await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["title"] == "Kitchen"
    assert result3["data"][CONF_DEVICE_TYPE] == DEVICE_TYPE_ZEN32
    assert result3["data"][CONF_DEVICE_ID] == "device-abc"
    assert result3["data"][CONF_LED_COUNT] == 5


async def test_duplicate_device_aborts(hass: HomeAssistant) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DEVICE_TYPE_ZEN32}:device-abc",
        data={
            CONF_DEVICE_TYPE: DEVICE_TYPE_ZEN32,
            CONF_DEVICE_ID: "device-abc",
        },
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
            {
                CONF_DEVICE_ID: "device-abc",
                CONF_FRIENDLY_NAME: "Kitchen",
                CONF_LED_COUNT: 5,
            },
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
        # Device exists but its config entry doesn't belong to the expected integration.
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
            {
                CONF_DEVICE_ID: "device-abc",
                CONF_FRIENDLY_NAME: "Kitchen",
                CONF_LED_COUNT: 5,
            },
        )

    assert result3["type"] == FlowResultType.FORM
    assert result3["errors"] == {CONF_DEVICE_ID: "wrong_integration"}
