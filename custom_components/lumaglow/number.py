"""Strombegrenzung der LEDs, Dauer pro GIF in der Playlist, Effekt-Geschwindigkeit und -Stärke (Strip)."""

from __future__ import annotations

from dataclasses import replace

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfElectricCurrent, UnitOfTime
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
    entities: list[NumberEntity] = [LumaGlowMaxCurrent(coordinator)]
    if coordinator.data.playlist is not None:
        entities.append(LumaGlowPlaylistSeconds(coordinator))
    if coordinator.data.strip:
        entities += [LumaGlowEffectNumber(coordinator, "speed"), LumaGlowEffectNumber(coordinator, "intensity")]
    async_add_entities(entities)


class LumaGlowMaxCurrent(LumaGlowEntity, NumberEntity):
    _attr_translation_key = "max_current"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.MILLIAMPERE
    # 0 = keine Grenze; die Firmware hebt 1–499 auf 500 an (Maximum 20000)
    _attr_native_min_value = 0
    _attr_native_max_value = 20000
    _attr_native_step = 100
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: LumaGlowCoordinator) -> None:
        super().__init__(coordinator, "max_current")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.info.get("maxCurrent")

    async def async_set_native_value(self, value: float) -> None:
        try:
            # Antwort = /api/info mit dem neuen Zustand
            info = await self.coordinator.client.set_display(maxCurrent=int(value))
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.async_set_updated_data(replace(self.coordinator.data, info=info))


class LumaGlowPlaylistSeconds(LumaGlowEntity, NumberEntity):
    """Wie lange jedes GIF der Playlist läuft (Firmware: 10 s bis 60 min)."""

    _attr_translation_key = "playlist_seconds"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_native_min_value = 10
    _attr_native_max_value = 3600
    _attr_native_step = 5
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: LumaGlowCoordinator) -> None:
        super().__init__(coordinator, "playlist_seconds")

    @property
    def native_value(self) -> int | None:
        playlist = self.coordinator.data.playlist
        return playlist.get("seconds") if playlist else None

    async def async_set_native_value(self, value: float) -> None:
        try:
            playlist = await self.coordinator.client.set_playlist(seconds=int(value))
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.async_set_updated_data(replace(self.coordinator.data, playlist=playlist))


class LumaGlowEffectNumber(LumaGlowEntity, NumberEntity):
    """Geschwindigkeit bzw. Stärke des Effekts am LED-Strip in %, die Firmware rechnet 0–255."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: LumaGlowCoordinator, field: str) -> None:
        super().__init__(coordinator, f"effect_{field}")
        self._field = field
        self._attr_translation_key = f"effect_{field}"

    @property
    def native_value(self) -> int | None:
        light = self.coordinator.data.light
        return round(light[self._field] * 100 / 255) if light and self._field in light else None

    async def async_set_native_value(self, value: float) -> None:
        try:
            light = await self.coordinator.client.set_light(**{self._field: round(value * 255 / 100)})
            # Ein Effekt-Wert schaltet das Licht ein: Ein/Aus und Helligkeit neu lesen
            info = await self.coordinator.client.get_info()
        except LumaGlowError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.async_set_updated_data(replace(self.coordinator.data, info=info, light=light))
