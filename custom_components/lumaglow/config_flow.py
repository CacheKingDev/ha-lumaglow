"""Einrichtung: automatisch per Zeroconf (_lumaglow._tcp) oder manuell mit Host/IP."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import LumaGlowClient, LumaGlowError
from .const import DOMAIN


class LumaGlowConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._name: str | None = None

    async def _fetch_info(self, host: str) -> dict[str, Any]:
        client = LumaGlowClient(async_get_clientsession(self.hass), host)
        return await client.get_info()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            try:
                info = await self._fetch_info(host)
            except LumaGlowError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(format_mac(info["mac"]))
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(title=info.get("hostname") or host, data={CONF_HOST: host})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default="lumaglow.local"): str}),
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        host = discovery_info.host
        mac = discovery_info.properties.get("mac")
        if mac:
            await self.async_set_unique_id(format_mac(mac))
            # IP hat sich geändert → bestehenden Eintrag aktualisieren
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        try:
            info = await self._fetch_info(host)
        except LumaGlowError:
            return self.async_abort(reason="cannot_connect")
        if not mac:
            await self.async_set_unique_id(format_mac(info["mac"]))
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._host = host
        self._name = info.get("hostname") or host
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title=self._name, data={CONF_HOST: self._host})

        self._set_confirm_only()
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"name": self._name, "host": self._host},
        )
