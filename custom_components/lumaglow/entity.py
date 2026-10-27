"""Gemeinsame Basis: ein Gerät pro Matrix, Zustand vom Coordinator."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import LumaGlowCoordinator


class LumaGlowEntity(CoordinatorEntity[LumaGlowCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: LumaGlowCoordinator, key: str) -> None:
        super().__init__(coordinator)
        mac = coordinator.config_entry.unique_id
        info = coordinator.data.info
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={(CONNECTION_NETWORK_MAC, mac)},
            manufacturer=MANUFACTURER,
            model=f"16x16 Matrix ({info.get('chip', '?')})",
            name=info.get("hostname") or "LumaGlow",
            sw_version=info.get("version") or info.get("build"),
            configuration_url=f"http://{coordinator.client.host}",
        )
