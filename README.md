# LED Controller

Home Assistant custom integration for driving the status LEDs on smart switches and scene
controllers from automations. Wraps `zwave_js` and `zha` service calls so each LED appears as
a first-class `light.*` entity and can also be set via integration-specific services.

## Supported devices

| Model | Radio | LEDs | Notes |
|-------|-------|------|-------|
| Zooz ZEN32 scene controller | Z-Wave | 5 (4 buttons + 1 relay) | 7-color palette, 3 brightness levels |
| Inovelli VZW32-SN Red mmWave dimmer | Z-Wave | 4 | 0–255 hue + 0–100 intensity |
| Inovelli VZM35-SN Blue fan switch | Zigbee (ZHA) | 7 | 0–255 hue + 0–100 intensity |

## Install via HACS

1. HACS → Integrations → ⋮ → Custom repositories
2. Add this repository as type **Integration**
3. Install **LED Controller**, restart Home Assistant
4. Settings → Devices & Services → Add Integration → **LED Controller**
5. Pick the device type and the backing z-wave / zigbee device

## Services

- `led_controller.set_led` — set one or more LEDs to a color/brightness.
- `led_controller.clear_led` — turn LED(s) off.
- `led_controller.set_scene` — atomic multi-LED update.

Color accepts canonical names (`red`, `green`, `blue`, `purple`, `cyan`, ...), `hsv:H,S,V`, or
`#RRGGBB`. Devices with a limited palette (ZEN32) snap to the nearest supported color and log a
warning.

## Entities

Each LED is exposed as a `light.<name>_led_<n>` entity. Inovelli devices support HS color mode;
ZEN32 LEDs expose on/off with a fixed-palette color attribute.

## References

- VZW32-SN z-wave parameter table from Inovelli Help Center.
- VZM35-SN ZHA cluster spec from `zigpy/zha-device-handlers` (shared Inovelli 0xFC31 cluster).
