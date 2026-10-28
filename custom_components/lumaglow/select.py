"""GIF-Auswahl als eigene Entität (gleiche Funktion wie der Licht-Effekt, aber ohne Licht-Dialog)."""

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
    async_add_entities([LumaGlowGIFSelect(entry.runtime_data)])


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
        self.coordinator.async_set_updated_data(replace(self.coordinator.data, current_gif=current))
