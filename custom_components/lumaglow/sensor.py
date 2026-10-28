"""Sensoren: geschätzter LED-Strom und -Leistung, Diagnose (WLAN-Signal, freier Speicher, letzter Neustart)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfInformation,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import LumaGlowConfigEntry, LumaGlowCoordinator
from .entity import LumaGlowEntity


@dataclass(frozen=True, kw_only=True)
class LumaGlowSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


LED_VOLTAGE = 5.0  # V, Versorgung der WS2812


def _current_ma(info: dict[str, Any]) -> int | None:
    # Mittel der letzten 10 s (Firmware ab v0.8.0), sonst Wert des letzten Bildes
    return info.get("currentAvg", info.get("current"))


def _power_w(info: dict[str, Any]) -> float | None:
    current = _current_ma(info)
    return None if current is None else round(current * LED_VOLTAGE / 1000, 2)


SENSORS = (
    LumaGlowSensorDescription(
        key="current",
        translation_key="current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_current_ma,
    ),
    LumaGlowSensorDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_power_w,
    ),
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
    coordinator = entry.runtime_data
    async_add_entities([*(LumaGlowSensor(coordinator, d) for d in SENSORS), LumaGlowBootTimeSensor(coordinator)])


class LumaGlowSensor(LumaGlowEntity, SensorEntity):
    entity_description: LumaGlowSensorDescription

    def __init__(self, coordinator: LumaGlowCoordinator, description: LumaGlowSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data.info)


# Abfragedauer und ganze Sekunden verschieben den errechneten Startzeitpunkt leicht;
# erst eine größere Abweichung gilt als Neustart
BOOT_TIME_TOLERANCE = timedelta(seconds=30)


class LumaGlowBootTimeSensor(LumaGlowEntity, SensorEntity):
    """Zeitpunkt des letzten Starts, errechnet aus `uptime` (Sekunden seit dem Start)."""

    _attr_translation_key = "boot_time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LumaGlowCoordinator) -> None:
        super().__init__(coordinator, "boot_time")
        self._update_boot_time()

    def _update_boot_time(self) -> None:
        uptime = self.coordinator.data.info.get("uptime")
        if uptime is None:
            self._attr_native_value = None
            return
        boot = (dt_util.utcnow() - timedelta(seconds=uptime)).replace(microsecond=0)
        previous = self._attr_native_value
        if previous is None or abs(boot - previous) > BOOT_TIME_TOLERANCE:
            self._attr_native_value = boot

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_boot_time()
        super()._handle_coordinator_update()
