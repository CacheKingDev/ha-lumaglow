"""Playlist an/aus und gemischte Reihenfolge (Firmware ab v0.10.0)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
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
    if coordinator.data.playlist is None:
        return   # ältere Firmware ohne Playlist
    async_add_entities([LumaGlowPlaylistSwitch(coordinator), LumaGlowShuffleSwitch(coordinator)])


class _PlaylistSwitch(LumaGlowEntity, SwitchEntity):
    _field: str

    def __init__(self, coordinator: LumaGlowCoordinator, key: str) -> None:
        super().__init__(coordinator, key)

    @property
    def is_on(self) -> bool | None:
        playlist = self.coordinator.data.playlist
        return bool(playlist.get(self._field)) if playlist else None

    async def _set(self, on: bool) -> None:
        try:
            # Antwort = Playlist mit neuem Zustand
            playlist = await self.coordinator.client.set_playlist(**{self._field: on})
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.async_set_updated_data(replace(self.coordinator.data, playlist=playlist))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)


class LumaGlowPlaylistSwitch(_PlaylistSwitch):
    """Playlist starten/beenden. Welche GIFs dabei sind, legt das Webinterface fest."""

    _attr_translation_key = "playlist"
    _field = "active"

    def __init__(self, coordinator: LumaGlowCoordinator) -> None:
        super().__init__(coordinator, "playlist")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        playlist = self.coordinator.data.playlist
        if not playlist:
            return None
        return {"gifs": playlist.get("items", []), "current": playlist.get("current") or None}

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not (self.coordinator.data.playlist or {}).get("items"):
            raise HomeAssistantError("Die Playlist ist leer. Wähle im Webinterface GIFs für die Playlist aus.")
        await self._set(True)
        # Das erste GIF läuft sofort: GIF-Auswahl und Vorschau nicht erst nach 10 s nachziehen
        await self.coordinator.async_request_refresh()


class LumaGlowShuffleSwitch(_PlaylistSwitch):
    _attr_translation_key = "playlist_shuffle"
    _attr_entity_category = EntityCategory.CONFIG
    _field = "shuffle"

    def __init__(self, coordinator: LumaGlowCoordinator) -> None:
        super().__init__(coordinator, "playlist_shuffle")
