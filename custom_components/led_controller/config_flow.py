"""Config flow for led_controller."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_FRIENDLY_NAME,
    CONF_Z2M_BASE_TOPIC,
    CONF_Z2M_NAME,
    DEFAULT_Z2M_BASE_TOPIC,
    DEVICE_TYPE_INTEGRATION,
    DEVICE_TYPE_VZM35,
    DEVICE_TYPES,
    DOMAIN,
)


class LedControllerConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._device_type: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        if user_input is not None:
            self._device_type = user_input[CONF_DEVICE_TYPE]
            return await self.async_step_device()

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_TYPE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(DEVICE_TYPES),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key=CONF_DEVICE_TYPE,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_device(self, user_input: dict[str, Any] | None = None) -> Any:
        assert self._device_type is not None
        errors: dict[str, str] = {}
        is_vzm35 = self._device_type == DEVICE_TYPE_VZM35

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            registry = dr.async_get(self.hass)
            entry = registry.async_get(device_id)
            if entry is None:
                errors[CONF_DEVICE_ID] = "device_not_found"
            else:
                expected_integration = DEVICE_TYPE_INTEGRATION[self._device_type]
                if not any(
                    cfg in entry.config_entries
                    for cfg in _integration_entry_ids(self.hass, expected_integration)
                ):
                    errors[CONF_DEVICE_ID] = "wrong_integration"

            if is_vzm35 and not user_input.get(CONF_Z2M_NAME):
                errors[CONF_Z2M_NAME] = "required"

            if not errors:
                await self.async_set_unique_id(f"{self._device_type}:{device_id}")
                self._abort_if_unique_id_configured()
                default_name = (entry.name_by_user or entry.name) if entry else device_id
                friendly = user_input.get(CONF_FRIENDLY_NAME) or default_name
                data: dict[str, Any] = {
                    CONF_DEVICE_TYPE: self._device_type,
                    CONF_DEVICE_ID: device_id,
                    CONF_FRIENDLY_NAME: friendly,
                }
                if is_vzm35:
                    data[CONF_Z2M_NAME] = user_input[CONF_Z2M_NAME]
                    data[CONF_Z2M_BASE_TOPIC] = (
                        user_input.get(CONF_Z2M_BASE_TOPIC) or DEFAULT_Z2M_BASE_TOPIC
                    )
                return self.async_create_entry(title=friendly, data=data)

        expected_integration = DEVICE_TYPE_INTEGRATION[self._device_type]
        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_DEVICE_ID): selector.DeviceSelector(
                selector.DeviceSelectorConfig(integration=expected_integration),
            ),
            vol.Optional(CONF_FRIENDLY_NAME): selector.TextSelector(),
        }
        if is_vzm35:
            schema_dict[vol.Required(CONF_Z2M_NAME)] = selector.TextSelector()
            schema_dict[vol.Optional(CONF_Z2M_BASE_TOPIC, default=DEFAULT_Z2M_BASE_TOPIC)] = (
                selector.TextSelector()
            )

        return self.async_show_form(
            step_id="device", data_schema=vol.Schema(schema_dict), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return LedControllerOptionsFlow(entry)


class LedControllerOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = {**self._entry.data, **self._entry.options}
        schema_dict: dict[Any, Any] = {
            vol.Optional(
                CONF_FRIENDLY_NAME,
                default=data.get(CONF_FRIENDLY_NAME, ""),
            ): selector.TextSelector(),
        }
        if data[CONF_DEVICE_TYPE] == DEVICE_TYPE_VZM35:
            schema_dict[vol.Required(CONF_Z2M_NAME, default=data.get(CONF_Z2M_NAME, ""))] = (
                selector.TextSelector()
            )
            schema_dict[
                vol.Optional(
                    CONF_Z2M_BASE_TOPIC,
                    default=data.get(CONF_Z2M_BASE_TOPIC, DEFAULT_Z2M_BASE_TOPIC),
                )
            ] = selector.TextSelector()
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))


def _integration_entry_ids(hass, integration: str) -> set[str]:
    return {e.entry_id for e in hass.config_entries.async_entries(integration)}
