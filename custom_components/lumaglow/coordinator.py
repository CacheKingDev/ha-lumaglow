"""Fragt den Gerätezustand regelmäßig ab."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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


class LumaGlowCoordinator(DataUpdateCoordinator[LumaGlowData]):
    config_entry: LumaGlowConfigEntry

    def __init__(self, hass: HomeAssistant, entry: LumaGlowConfigEntry, client: LumaGlowClient) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.client = client

    async def _async_update_data(self) -> LumaGlowData:
        try:
            info = await self.client.get_info()
            gifs = await self.client.get_gifs()
        except LumaGlowError as err:
            raise UpdateFailed(str(err)) from err

        current = gifs.get("current") or None
        return LumaGlowData(
            info=info,
            gifs=[g["name"] for g in gifs.get("gifs", [])],
            current_gif=current if gifs.get("playing") else None,
        )
