"""Nächstes GIF der Playlist (Firmware ab v0.10.0)."""

from __future__ import annotations

from dataclasses import replace

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import LumaGlowError
from .coordinator import LumaGlowConfigEntry, LumaGlowCoordinator
from .entity import LumaGlowEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LumaGlowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    if coordinator.data.playlist is not None:
        async_add_entities([LumaGlowNextButton(coordinator)])


class LumaGlowNextButton(LumaGlowEntity, ButtonEntity):
    _attr_translation_key = "playlist_next"

    def __init__(self, coordinator: LumaGlowCoordinator) -> None:
        super().__init__(coordinator, "playlist_next")

    @property
    def available(self) -> bool:
        # Nur sinnvoll, solange die Playlist läuft
        playlist = self.coordinator.data.playlist if self.coordinator.data else None
        return super().available and bool(playlist and playlist.get("active"))

    async def async_press(self) -> None:
        try:
            playlist = await self.coordinator.client.set_playlist(next=1)
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        current = playlist.get("current") or self.coordinator.data.current_gif
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, playlist=playlist, current_gif=current)
        )
