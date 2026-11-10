"""Fragt den Gerätezustand regelmäßig ab."""

from __future__ import annotations

from dataclasses import dataclass, replace
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LumaGlowClient, LumaGlowError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type LumaGlowConfigEntry = ConfigEntry[LumaGlowCoordinator]


@dataclass
class LumaGlowData:
    info: dict[str, Any]
    gifs: list[str]
    current_gif: str | None   # nur gesetzt, wenn das GIF gerade läuft
    playlist: dict[str, Any] | None = None   # None = Firmware ohne Playlist (vor v0.10.0)
    light: dict[str, Any] | None = None      # nur am LED-Strip: effect, effectName, color, color2, speed, intensity

    @property
    def strip(self) -> bool:
        """LED-Strip statt Matrix (Firmware ab v0.11.0): Farben und Effekte statt GIFs."""
        return bool(self.info.get("strip"))

    def single_gif(self, current: str | None) -> LumaGlowData:
        """Zustand nach Auswahl eines einzelnen GIFs bzw. "Kein GIF": die Firmware beendet dabei die Playlist."""
        playlist = {**self.playlist, "active": False} if self.playlist else self.playlist
        return replace(self, current_gif=current, playlist=playlist)


class LumaGlowCoordinator(DataUpdateCoordinator[LumaGlowData]):
    config_entry: LumaGlowConfigEntry

    def __init__(self, hass: HomeAssistant, entry: LumaGlowConfigEntry, client: LumaGlowClient) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.client = client
        # Effekte des Strips (id, name, color, color2, speed, intensity); ändern sich nur mit der Firmware
        self.effects: list[dict[str, Any]] = []
        self._strip: bool | None = None

    async def _async_update_data(self) -> LumaGlowData:
        try:
            info = await self.client.get_info()
        except LumaGlowError as err:
            raise UpdateFailed(str(err)) from err

        # Unter dem Host antwortet ein anderes Gerät (z. B. zwei Matrizen mit gleichem mDNS-Namen):
        # nicht dessen Zustand anzeigen oder es steuern. Die Zeroconf-Erkennung setzt die richtige IP.
        mac = format_mac(info.get("mac", ""))
        if mac != self.config_entry.unique_id:
            raise UpdateFailed(
                f"{self.client.host} gehört zu {mac or 'unbekannt'}, erwartet {self.config_entry.unique_id}"
            )

        # Matrix ↔ Strip (nach Werksreset neu eingerichtet): andere Entitäten, Eintrag neu laden
        strip = bool(info.get("strip"))
        if self._strip is not None and strip != self._strip:
            _LOGGER.info("%s ist jetzt %s, lade neu", self.client.host, "ein LED-Strip" if strip else "eine Matrix")
            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
        self._strip = strip

        if strip:
            # Keine GIFs; den Zustand liefert /api/info, die Effektliste einmal /api/light
            if not self.effects:
                try:
                    self.effects = (await self.client.get_light()).get("effects", [])
                except LumaGlowError as err:
                    raise UpdateFailed(str(err)) from err
            return LumaGlowData(info=info, gifs=[], current_gif=None, light=info.get("light"))

        try:
            gifs = await self.client.get_gifs()
        except LumaGlowError as err:
            raise UpdateFailed(str(err)) from err

        # Playlist nur abfragen, wenn die Firmware sie kennt (/api/info hat dann "playlist")
        playlist = None
        if "playlist" in info:
            try:
                playlist = await self.client.get_playlist()
            except LumaGlowError as err:
                raise UpdateFailed(str(err)) from err

        current = gifs.get("current") or None
        return LumaGlowData(
            info=info,
            gifs=[g["name"] for g in gifs.get("gifs", [])],
            current_gif=current if gifs.get("playing") else None,
            playlist=playlist,
        )
