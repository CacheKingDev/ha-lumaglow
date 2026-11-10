"""Matrix als Licht (an/aus, Helligkeit, GIF als Effekt) bzw. LED-Strip als Farblicht mit Effekten."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.color import color_temperature_to_rgb

from .api import LumaGlowError
from .const import NO_GIF as EFFECT_NONE
from .coordinator import LumaGlowConfigEntry, LumaGlowCoordinator
from .entity import LumaGlowEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LumaGlowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    if coordinator.data.strip:
        async_add_entities([LumaGlowStripLight(coordinator)])
    else:
        async_add_entities([LumaGlowLight(coordinator)])


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
        data = self.coordinator.data
        try:
            display: dict[str, Any] = {"power": True}
            if ATTR_BRIGHTNESS in kwargs:
                # Firmware erlaubt 1–255 (0 = aus wäre power=0)
                display["brightness"] = max(1, kwargs[ATTR_BRIGHTNESS])
            # Antwort = /api/info mit dem neuen Zustand
            data = replace(data, info=await client.set_display(**display))

            effect = kwargs.get(ATTR_EFFECT)
            if effect == EFFECT_NONE:
                await client.stop_gif()
                data = data.single_gif(None)
            elif effect is not None:
                await client.play_gif(effect)
                data = data.single_gif(effect)
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        # Zustand sofort übernehmen statt auf die nächste Abfrage zu warten
        # (async_request_refresh hätte 10 s Abklingzeit beim schnellen Hin- und Herschalten)
        self.coordinator.async_set_updated_data(data)

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            info = await self.coordinator.client.set_display(power=False)
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.async_set_updated_data(replace(self.coordinator.data, info=info))


# Weißton-Bereich wie im Webinterface der Firmware
STRIP_MIN_KELVIN = 1900
STRIP_MAX_KELVIN = 6500
EFFECT_SOLID = 0   # "Farbe" (Effects.h)
PALETTE_DEFAULT = 0   # "Standard": Farben des Effekts
PALETTE_COLORS = 1    # "Farbe 1+2": Verlauf aus den gewählten Farben; ab 2 eigene Farben der Palette


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


class LumaGlowStripLight(LumaGlowEntity, LightEntity):
    """LED-Strip (Firmware ab v0.11.0): Farbe, Weißton, Helligkeit und Effekt."""

    _attr_name = None   # Entität heißt wie das Gerät
    _attr_supported_color_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_min_color_temp_kelvin = STRIP_MIN_KELVIN
    _attr_max_color_temp_kelvin = STRIP_MAX_KELVIN

    def __init__(self, coordinator: LumaGlowCoordinator) -> None:
        super().__init__(coordinator, "light")
        # Die Firmware kennt nur RGB: zuletzt gewählten Weißton merken, solange die Farbe dazu passt
        self._kelvin: int | None = None
        self._kelvin_color: str | None = None

    @property
    def _light(self) -> dict[str, Any]:
        return self.coordinator.data.light or {}

    def _effect_by_id(self, effect_id: int | None) -> dict[str, Any]:
        return next((e for e in self.coordinator.effects if e.get("id") == effect_id), {})

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.info.get("power"))

    @property
    def brightness(self) -> int | None:
        return self.coordinator.data.info.get("brightness")

    @property
    def color_mode(self) -> ColorMode:
        if self._kelvin is not None and self._light.get("color") == self._kelvin_color:
            return ColorMode.COLOR_TEMP
        return ColorMode.RGB

    @property
    def color_temp_kelvin(self) -> int | None:
        return self._kelvin if self.color_mode == ColorMode.COLOR_TEMP else None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        color = self._light.get("color")
        if not color or len(color) != 7:
            return None
        return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))

    @property
    def effect_list(self) -> list[str]:
        return [e["name"] for e in self.coordinator.effects]

    @property
    def effect(self) -> str | None:
        return self._light.get("effectName")

    async def async_turn_on(self, **kwargs: Any) -> None:
        client = self.coordinator.client
        params: dict[str, Any] = {}

        effect = kwargs.get(ATTR_EFFECT)
        if effect is not None:
            match = next((e for e in self.coordinator.effects if e["name"] == effect), None)
            if match is None:
                raise HomeAssistantError(f"Unbekannter Effekt: {effect}")
            params["effect"] = match["id"]

        if ATTR_RGB_COLOR in kwargs:
            params["color"] = _hex(kwargs[ATTR_RGB_COLOR])
            self._kelvin = None
        elif ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = int(kwargs[ATTR_COLOR_TEMP_KELVIN])
            params["color"] = _hex(color_temperature_to_rgb(kelvin))
            self._kelvin, self._kelvin_color = kelvin, params["color"]

        # Wie im Webinterface: Eine Palette mit eigenen Farben würde die Farbe überdecken → Palette "Standard".
        # Sonst bei einem Effekt ohne eigene Farbe (Regenbogen, Feuer …) auf "Farbe" umschalten.
        if "color" in params:
            palette = self._light.get("palette", PALETTE_DEFAULT)
            if palette > PALETTE_COLORS:
                params["palette"] = PALETTE_DEFAULT
            elif "effect" not in params and palette != PALETTE_COLORS:
                if not self._effect_by_id(self._light.get("effect")).get("color", True):
                    params["effect"] = EFFECT_SOLID

        try:
            display: dict[str, Any] = {"power": True}
            if ATTR_BRIGHTNESS in kwargs:
                # Firmware erlaubt 1–255 (0 = aus wäre power=0)
                display["brightness"] = max(1, kwargs[ATTR_BRIGHTNESS])
            info = await client.set_display(**display)
            light = await client.set_light(**params) if params else self.coordinator.data.light
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.async_set_updated_data(replace(self.coordinator.data, info=info, light=light))

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            info = await self.coordinator.client.set_display(power=False)
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.async_set_updated_data(replace(self.coordinator.data, info=info))
