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
    CONF_LED_COUNT,
    DEVICE_TYPE_INTEGRATION,
    DEVICE_TYPE_LED_COUNT,
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

            if not errors:
                await self.async_set_unique_id(f"{self._device_type}:{device_id}")
                self._abort_if_unique_id_configured()
                default_name = (entry.name_by_user or entry.name) if entry else device_id
                friendly = user_input.get(CONF_FRIENDLY_NAME) or default_name
                return self.async_create_entry(
                    title=friendly,
                    data={
                        CONF_DEVICE_TYPE: self._device_type,
                        CONF_DEVICE_ID: device_id,
                        CONF_FRIENDLY_NAME: friendly,
                        CONF_LED_COUNT: user_input.get(
                            CONF_LED_COUNT, DEVICE_TYPE_LED_COUNT[self._device_type]
                        ),
                    },
                )

        expected_integration = DEVICE_TYPE_INTEGRATION[self._device_type]
        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID): selector.DeviceSelector(
                    selector.DeviceSelectorConfig(integration=expected_integration),
                ),
                vol.Optional(CONF_FRIENDLY_NAME): selector.TextSelector(),
                vol.Required(
                    CONF_LED_COUNT,
                    default=DEVICE_TYPE_LED_COUNT[self._device_type],
                ): vol.All(int, vol.Range(min=1, max=16)),
            }
        )
        return self.async_show_form(step_id="device", data_schema=schema, errors=errors)

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
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_FRIENDLY_NAME,
                    default=data.get(CONF_FRIENDLY_NAME, ""),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_LED_COUNT,
                    default=data.get(
                        CONF_LED_COUNT,
                        DEVICE_TYPE_LED_COUNT[data[CONF_DEVICE_TYPE]],
                    ),
                ): vol.All(int, vol.Range(min=1, max=16)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _integration_entry_ids(hass, integration: str) -> set[str]:
    return {e.entry_id for e in hass.config_entries.async_entries(integration)}
