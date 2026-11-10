"""GIF-Auswahl als eigene Entität (gleiche Funktion wie der Licht-Effekt, aber ohne Licht-Dialog);
am LED-Strip die Palette."""

from __future__ import annotations

from dataclasses import replace

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import LumaGlowError
from .const import NO_GIF
from .coordinator import LumaGlowConfigEntry, LumaGlowCoordinator
from .entity import LumaGlowEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LumaGlowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    if coordinator.data.strip:
        # LED-Strip: keine GIFs, Effekte über das Licht; Paletten ab Firmware v0.12.0
        if coordinator.palettes:
            async_add_entities([LumaGlowPaletteSelect(coordinator)])
        return
    async_add_entities([LumaGlowGIFSelect(coordinator)])


class LumaGlowGIFSelect(LumaGlowEntity, SelectEntity):
    _attr_translation_key = "gif"

    def __init__(self, coordinator: LumaGlowCoordinator) -> None:
        super().__init__(coordinator, "gif")

    @property
    def options(self) -> list[str]:
        return [NO_GIF, *self.coordinator.data.gifs]

    @property
    def current_option(self) -> str:
        current = self.coordinator.data.current_gif
        # Muss in options stehen; ein gerade gelöschtes GIF kann noch laufen
        return current if current in self.coordinator.data.gifs else NO_GIF

    async def async_select_option(self, option: str) -> None:
        client = self.coordinator.client
        try:
            if option == NO_GIF:
                await client.stop_gif()
            else:
                await client.play_gif(option)
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        current = None if option == NO_GIF else option
        self.coordinator.async_set_updated_data(self.coordinator.data.single_gif(current))


class LumaGlowPaletteSelect(LumaGlowEntity, SelectEntity):
    """Farbverlauf, der sich auf den Effekt legt (LED-Strip, Firmware ab v0.12.0)."""

    _attr_translation_key = "palette"

    def __init__(self, coordinator: LumaGlowCoordinator) -> None:
        super().__init__(coordinator, "palette")

    @property
    def options(self) -> list[str]:
        return [p["name"] for p in self.coordinator.palettes]

    @property
    def current_option(self) -> str | None:
        light = self.coordinator.data.light or {}
        name = light.get("paletteName")
        return name if name in self.options else None

    async def async_select_option(self, option: str) -> None:
        match = next((p for p in self.coordinator.palettes if p["name"] == option), None)
        if match is None:
            raise HomeAssistantError(f"Unbekannte Palette: {option}")
        client = self.coordinator.client
        try:
            light = await client.set_light(palette=match["id"])
            # Eine Änderung am Licht schaltet es ein: Ein/Aus und Helligkeit neu lesen
            info = await client.get_info()
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.async_set_updated_data(replace(self.coordinator.data, info=info, light=light))
