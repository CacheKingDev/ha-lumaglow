"""Diagnose-Sensoren: WLAN-Signal und freier Speicher."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LumaGlowConfigEntry, LumaGlowCoordinator
from .entity import LumaGlowEntity


@dataclass(frozen=True, kw_only=True)
class LumaGlowSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSORS = (
    LumaGlowSensorDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda info: info.get("rssi"),
    ),
    LumaGlowSensorDescription(
        key="fs_free",
        translation_key="fs_free",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.KILOBYTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda info: info.get("fsTotal", 0) - info.get("fsUsed", 0),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LumaGlowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(LumaGlowSensor(entry.runtime_data, d) for d in SENSORS)


class LumaGlowSensor(LumaGlowEntity, SensorEntity):
    entity_description: LumaGlowSensorDescription

    def __init__(self, coordinator: LumaGlowCoordinator, description: LumaGlowSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data.info)
