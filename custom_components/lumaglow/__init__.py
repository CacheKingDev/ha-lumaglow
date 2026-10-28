"""LumaGlow – 16x16-Pixelmatrix im lokalen Netz (REST-API der Firmware)."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LumaGlowClient
from .coordinator import LumaGlowConfigEntry, LumaGlowCoordinator

PLATFORMS = [Platform.IMAGE, Platform.LIGHT, Platform.NUMBER, Platform.SELECT, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: LumaGlowConfigEntry) -> bool:
    client = LumaGlowClient(async_get_clientsession(hass), entry.data[CONF_HOST])
    coordinator = LumaGlowCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LumaGlowConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
