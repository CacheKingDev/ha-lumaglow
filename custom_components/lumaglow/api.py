"""HTTP-Client für die REST-API der LumaGlow-Firmware (WebUI.cpp)."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import REQUEST_TIMEOUT


class LumaGlowError(Exception):
    """Gerät nicht erreichbar oder Fehlerantwort."""


class LumaGlowClient:
    """Spricht die Endpunkte unter http://<host>/api/ an."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self._session = session
        self.host = host

    async def _request(self, method: str, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"http://{self.host}{path}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                # Die Firmware liest Parameter per arg() → Formular-Body (x-www-form-urlencoded)
                async with self._session.request(method, url, data=data) as resp:
                    body = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise LumaGlowError(f"{method} {url}: {err}") from err

        if resp.status >= 400:
            message = body.get("error") if isinstance(body, dict) else None
            raise LumaGlowError(f"{method} {url}: HTTP {resp.status} {message or ''}".strip())
        return body

    async def get_info(self) -> dict[str, Any]:
        """Geräte-Info und Anzeige-Einstellungen (power, brightness, gamma, …)."""
        return await self._request("GET", "/api/info")

    async def get_gifs(self) -> dict[str, Any]:
        """GIF-Liste, aktuelles GIF und ob es läuft."""
        return await self._request("GET", "/api/gifs")

    async def set_display(self, **values: Any) -> dict[str, Any]:
        """Anzeige ändern: power (0/1), brightness (1–255), gamma, format."""
        data = {key: int(v) if isinstance(v, bool) else v for key, v in values.items()}
        return await self._request("POST", "/api/display", data)

    async def play_gif(self, name: str) -> None:
        await self._request("POST", "/api/gifs/play", {"name": name})

    async def stop_gif(self) -> None:
        await self._request("POST", "/api/gifs/stop")
