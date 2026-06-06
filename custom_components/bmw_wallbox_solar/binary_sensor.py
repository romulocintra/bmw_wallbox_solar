"""Binary sensor platform for BMW Wallbox Solar integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BINARY_SENSOR_CHARGING,
    BINARY_SENSOR_CONNECTED,
    BINARY_SENSOR_GRID_EXPORT,
    BINARY_SENSOR_SOLAR_SUFFICIENT,
    DATA_SERVER,
    DATA_SOLAR_CONTROLLER,
    DOMAIN,
)
from .entity_base import BMWWallboxEntity


@dataclass(frozen=True)
class BMWWallboxBinarySensorDescription(BinarySensorEntityDescription):
    pass


BINARY_SENSORS: tuple[BMWWallboxBinarySensorDescription, ...] = (
    BMWWallboxBinarySensorDescription(
        key=BINARY_SENSOR_CHARGING,
        name="Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        icon="mdi:ev-station",
    ),
    BMWWallboxBinarySensorDescription(
        key=BINARY_SENSOR_CONNECTED,
        name="Wallbox Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:lan-connect",
    ),
    BMWWallboxBinarySensorDescription(
        key=BINARY_SENSOR_SOLAR_SUFFICIENT,
        name="Solar Power Sufficient",
        icon="mdi:solar-power",
    ),
    BMWWallboxBinarySensorDescription(
        key=BINARY_SENSOR_GRID_EXPORT,
        name="Grid Exporting",
        icon="mdi:transmission-tower-export",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    server = data[DATA_SERVER]
    solar_controller = data[DATA_SOLAR_CONTROLLER]

    async_add_entities([
        BMWWallboxBinarySensor(entry.entry_id, desc, server, solar_controller)
        for desc in BINARY_SENSORS
    ])


class BMWWallboxBinarySensor(BMWWallboxEntity, BinarySensorEntity):
    """Binary sensor for wallbox and solar states."""

    def __init__(self, entry_id, description, server, solar_controller):
        super().__init__(entry_id, description.key, server, solar_controller)
        self.entity_description = description
        self._attr_name = description.name

    @property
    def is_on(self) -> bool:
        key = self.entity_description.key
        sc = self._solar_controller
        cs = self._charger_state

        if key == BINARY_SENSOR_CHARGING:
            return cs.charging
        if key == BINARY_SENSOR_CONNECTED:
            return cs.connected
        if key == BINARY_SENSOR_SOLAR_SUFFICIENT:
            return sc.solar_surplus >= (sc.min_charge_current * 230 * 3)
        if key == BINARY_SENSOR_GRID_EXPORT:
            return sc.grid_power < 0
        return False
