"""Device abstraction for led_controller."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from homeassistant.core import HomeAssistant

from ..color import Hsv

_LOGGER = logging.getLogger(__name__)


@dataclass
class LedState:
    """Cached state for one LED."""

    on: bool = False
    color: Hsv | None = None
    brightness_pct: int | None = None
    mode: str | None = None  # device-specific raw value, e.g. ZEN32 mode
    extra: dict[str, object] = field(default_factory=dict)


class LedDevice(ABC):
    """Base class for a physical LED-bearing device."""

    model: str
    led_count: int
    supported_palette: frozenset[str]
    supports_hsv: bool

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id

    def validate_led(self, led_idx: int) -> None:
        if not 1 <= led_idx <= self.led_count:
            raise ValueError(f"{self.model}: led_idx {led_idx} out of range 1..{self.led_count}")

    def led_name(self, led_idx: int) -> str:
        """Display name for LED entity — subclasses override for device-specific labels."""
        return f"LED {led_idx}"

    @abstractmethod
    async def set_led(
        self,
        hass: HomeAssistant,
        led_idx: int,
        color: Hsv,
        brightness_pct: int,
        mode: str | None = None,
        transition: int | None = None,
    ) -> None: ...

    @abstractmethod
    async def clear_led(self, hass: HomeAssistant, led_idx: int) -> None: ...

    @abstractmethod
    async def read_all(self, hass: HomeAssistant) -> dict[int, LedState]:
        """Return best-effort current state keyed by led_idx."""
