"""Device class registry for led_controller."""

from __future__ import annotations

from ..const import DEVICE_TYPE_VZM35, DEVICE_TYPE_VZW32, DEVICE_TYPE_ZEN32
from .base import LedDevice, LedState
from .vzm35 import Vzm35Device
from .vzw32 import Vzw32Device
from .zen32 import Zen32Device

DEVICE_CLASSES: dict[str, type[LedDevice]] = {
    DEVICE_TYPE_ZEN32: Zen32Device,
    DEVICE_TYPE_VZW32: Vzw32Device,
    DEVICE_TYPE_VZM35: Vzm35Device,
}


def build_device(device_type: str, device_id: str, led_count: int | None = None) -> LedDevice:
    cls = DEVICE_CLASSES[device_type]
    return cls(device_id, led_count=led_count)


__all__ = [
    "DEVICE_CLASSES",
    "LedDevice",
    "LedState",
    "build_device",
]
