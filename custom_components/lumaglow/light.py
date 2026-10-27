"""Matrix als Licht: an/aus, Helligkeit, GIF als Effekt."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import LumaGlowError
from .coordinator import LumaGlowConfigEntry
from .entity import LumaGlowEntity

# Effekt, der das laufende GIF anhält (Matrix bleibt an, aber schwarz)
EFFECT_NONE = "Kein GIF"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LumaGlowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([LumaGlowLight(entry.runtime_data)])


class LumaGlowLight(LumaGlowEntity, LightEntity):
    _attr_name = None   # Entität heißt wie das Gerät
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "light")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.info.get("power"))

    @property
    def brightness(self) -> int | None:
        return self.coordinator.data.info.get("brightness")

    @property
    def effect_list(self) -> list[str]:
        return [EFFECT_NONE, *self.coordinator.data.gifs]

    @property
    def effect(self) -> str:
        return self.coordinator.data.current_gif or EFFECT_NONE

    async def async_turn_on(self, **kwargs: Any) -> None:
        client = self.coordinator.client
        try:
            display: dict[str, Any] = {"power": True}
            if ATTR_BRIGHTNESS in kwargs:
                # Firmware erlaubt 1–255 (0 = aus wäre power=0)
                display["brightness"] = max(1, kwargs[ATTR_BRIGHTNESS])
            await client.set_display(**display)

            effect = kwargs.get(ATTR_EFFECT)
            if effect == EFFECT_NONE:
                await client.stop_gif()
            elif effect is not None:
                await client.play_gif(effect)
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.client.set_display(power=False)
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
