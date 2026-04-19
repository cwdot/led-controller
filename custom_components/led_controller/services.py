"""Service handlers for led_controller.

Services are registered once per HA instance (not per config entry) and dispatch to the
`LedControllerCoordinator` associated with each targeted device_id.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .color import Hsv, parse_color, snap_to_palette
from .const import DOMAIN
from .coordinator import LedControllerCoordinator
from .devices import LedState

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_LED = "set_led"
SERVICE_CLEAR_LED = "clear_led"
SERVICE_SET_SCENE = "set_scene"


def _led_selector(value: Any) -> list[int] | str:
    """Accept int, 'all', list of ints, or comma-separated string."""
    if value == "all" or value is None:
        return "all"
    if isinstance(value, int):
        return [value]
    if isinstance(value, list):
        return [int(v) for v in value]
    if isinstance(value, str):
        if value.strip().lower() == "all":
            return "all"
        return [int(part) for part in value.split(",") if part.strip()]
    raise vol.Invalid(f"unrecognized led selector: {value!r}")


SET_LED_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): vol.Any(cv.string, [cv.string]),
        vol.Optional("area_id"): vol.Any(cv.string, [cv.string]),
        vol.Optional("entity_id"): vol.Any(cv.string, [cv.string]),
        vol.Required("led"): _led_selector,
        vol.Required("color"): cv.string,
        vol.Optional("brightness", default=100): vol.All(int, vol.Range(min=0, max=100)),
        vol.Optional("mode"): vol.In({"on", "off", "always_on", "always_off"}),
        vol.Optional("transition"): vol.All(int, vol.Range(min=0, max=255)),
    },
    extra=vol.ALLOW_EXTRA,
)

CLEAR_LED_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): vol.Any(cv.string, [cv.string]),
        vol.Optional("area_id"): vol.Any(cv.string, [cv.string]),
        vol.Optional("entity_id"): vol.Any(cv.string, [cv.string]),
        vol.Required("led"): _led_selector,
    },
    extra=vol.ALLOW_EXTRA,
)

SET_SCENE_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): vol.Any(cv.string, [cv.string]),
        vol.Optional("area_id"): vol.Any(cv.string, [cv.string]),
        vol.Optional("entity_id"): vol.Any(cv.string, [cv.string]),
        vol.Required("leds"): [
            vol.Schema(
                {
                    vol.Required("led"): vol.All(int, vol.Range(min=1)),
                    vol.Required("color"): cv.string,
                    vol.Optional("brightness", default=100): vol.All(
                        int, vol.Range(min=0, max=100)
                    ),
                    vol.Optional("mode"): vol.In({"on", "off", "always_on", "always_off"}),
                }
            )
        ],
    },
    extra=vol.ALLOW_EXTRA,
)


def async_register_services(hass: HomeAssistant) -> None:
    """Register services once. Re-registration is a no-op."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_LED):
        return

    async def _set_led(call: ServiceCall) -> None:
        coordinators = _resolve_coordinators(hass, call)
        led_selector = call.data["led"]
        color_input = call.data["color"]
        brightness = call.data.get("brightness", 100)
        mode = call.data.get("mode")
        transition = call.data.get("transition")

        raw = parse_color(color_input)
        for coord in coordinators:
            leds = _expand_leds(led_selector, coord.device.led_count)
            color_for_device = _adapt_color(raw, coord.device)
            for led_idx in leds:
                await coord.device.set_led(
                    hass, led_idx, color_for_device, brightness, mode=mode, transition=transition
                )
                coord.record_write(
                    led_idx,
                    LedState(on=True, color=color_for_device, brightness_pct=brightness, mode=mode),
                )

    async def _clear_led(call: ServiceCall) -> None:
        coordinators = _resolve_coordinators(hass, call)
        led_selector = call.data["led"]
        for coord in coordinators:
            leds = _expand_leds(led_selector, coord.device.led_count)
            for led_idx in leds:
                await coord.device.clear_led(hass, led_idx)
                coord.record_write(led_idx, LedState(on=False))

    async def _set_scene(call: ServiceCall) -> None:
        coordinators = _resolve_coordinators(hass, call)
        entries = call.data["leds"]
        for coord in coordinators:
            for entry in entries:
                raw = parse_color(entry["color"])
                color_for_device = _adapt_color(raw, coord.device)
                led_idx = entry["led"]
                brightness = entry.get("brightness", 100)
                mode = entry.get("mode")
                if led_idx < 1 or led_idx > coord.device.led_count:
                    _LOGGER.warning(
                        "set_scene: led %d out of range for %s (1..%d), skipping",
                        led_idx,
                        coord.device.model,
                        coord.device.led_count,
                    )
                    continue
                await coord.device.set_led(hass, led_idx, color_for_device, brightness, mode=mode)
                coord.record_write(
                    led_idx,
                    LedState(on=True, color=color_for_device, brightness_pct=brightness, mode=mode),
                )

    hass.services.async_register(DOMAIN, SERVICE_SET_LED, _set_led, schema=SET_LED_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_LED, _clear_led, schema=CLEAR_LED_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_SCENE, _set_scene, schema=SET_SCENE_SCHEMA)


def async_unregister_services(hass: HomeAssistant) -> None:
    """Called by __init__ only when the last config entry unloads."""
    for svc in (SERVICE_SET_LED, SERVICE_CLEAR_LED, SERVICE_SET_SCENE):
        if hass.services.has_service(DOMAIN, svc):
            hass.services.async_remove(DOMAIN, svc)


def _resolve_coordinators(hass: HomeAssistant, call: ServiceCall) -> list[LedControllerCoordinator]:
    """Find coordinators targeted by the service call's device_id / area / entity."""
    store: dict[str, LedControllerCoordinator] = hass.data.get(DOMAIN, {})
    requested = set(_as_list(call.data.get("device_id")))
    if not requested:
        # If targeted by area/entity, HA would have resolved via target expansion; for now
        # fall back to the 'all coordinators' interpretation when device_id is absent and no
        # coordinators were explicitly provided.
        if not call.data.get("area_id") and not call.data.get("entity_id"):
            raise vol.Invalid("device_id, area_id, or entity_id is required")
        # Area/entity resolution would need extra plumbing; treat as unsupported in v1.
        raise vol.Invalid("target by device_id for v1")
    matched = [coord for coord in store.values() if coord.entry.data.get("device_id") in requested]
    if not matched:
        raise vol.Invalid(f"no led_controller device matches {requested}")
    return matched


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _expand_leds(selector: list[int] | str, led_count: int) -> list[int]:
    if selector == "all":
        return list(range(1, led_count + 1))
    return [idx for idx in selector if 1 <= idx <= led_count]


def _adapt_color(raw: Hsv, device: Any) -> Hsv:
    """Snap-and-warn for palette-only devices; pass HSV through for others."""
    if device.supports_hsv:
        return raw
    name, lost = snap_to_palette(raw, device.supported_palette)
    if lost:
        _LOGGER.warning(
            "color %s snapped to %s for %s (palette: %s)",
            raw,
            name,
            device.model,
            sorted(device.supported_palette),
        )
    return parse_color(name)
