"""Sensor platform for BMW Wallbox Solar integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_SERVER,
    DATA_SOLAR_CONTROLLER,
    DOMAIN,
    SENSOR_CHARGING_SOURCE,
    SENSOR_CHARGING_STATE,
    SENSOR_CONNECTOR_STATUS,
    SENSOR_CURRENT_IMPORT,
    SENSOR_CURRENT_L1,
    SENSOR_CURRENT_L2,
    SENSOR_CURRENT_L3,
    SENSOR_CURRENT_OFFERED,
    SENSOR_DYNAMIC_CURRENT_TARGET,
    SENSOR_DYNAMIC_MODE,
    SENSOR_ENERGY_SESSION,
    SENSOR_ENERGY_TOTAL,
    SENSOR_FREQUENCY,
    SENSOR_POWER,
    SENSOR_POWER_ACTIVE_IMPORT,
    SENSOR_POWER_FACTOR,
    SENSOR_POWER_REACTIVE_IMPORT,
    SENSOR_SESSION_DURATION,
    SENSOR_SOLAR_POWER,
    SENSOR_SOLAR_SURPLUS,
    SENSOR_TEMPERATURE,
    SENSOR_TRANSACTION_ID,
    SENSOR_VOLTAGE,
    SENSOR_VOLTAGE_L1,
    SENSOR_VOLTAGE_L2,
    SENSOR_VOLTAGE_L3,
)
from .entity_base import BMWWallboxEntity


@dataclass(frozen=True)
class BMWWallboxSensorDescription(SensorEntityDescription):
    """Extended sensor description."""
    is_solar: bool = False
    enabled_by_default: bool = True


CHARGER_SENSORS: tuple[BMWWallboxSensorDescription, ...] = (
    # ── Core power sensors ─────────────────────────────────────────────────
    BMWWallboxSensorDescription(
        key=SENSOR_POWER,
        name="Charging Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:ev-station",
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_ENERGY_TOTAL,
        name="Energy Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:lightning-bolt",
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_ENERGY_SESSION,
        name="Energy Session",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-charging",
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_CURRENT_IMPORT,
        name="Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_CURRENT_OFFERED,
        name="Current Offered",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:current-ac",
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_VOLTAGE,
        name="Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Status ─────────────────────────────────────────────────────────────
    BMWWallboxSensorDescription(
        key=SENSOR_CONNECTOR_STATUS,
        name="Connector Status",
        icon="mdi:ev-plug-type2",
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_CHARGING_STATE,
        name="Charging State",
        icon="mdi:battery-charging-outline",
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_TRANSACTION_ID,
        name="Transaction ID",
        icon="mdi:identifier",
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_SESSION_DURATION,
        name="Session Duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-outline",
    ),
    # ── Per-phase (disabled by default) ────────────────────────────────────
    BMWWallboxSensorDescription(
        key=SENSOR_CURRENT_L1,
        name="Current L1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_CURRENT_L2,
        name="Current L2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_CURRENT_L3,
        name="Current L3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_VOLTAGE_L1,
        name="Voltage L1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_VOLTAGE_L2,
        name="Voltage L2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_VOLTAGE_L3,
        name="Voltage L3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_POWER_ACTIVE_IMPORT,
        name="Active Import Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_POWER_REACTIVE_IMPORT,
        name="Reactive Import Power",
        native_unit_of_measurement=UnitOfPower.VOLT_AMPERE_REACTIVE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_POWER_FACTOR,
        name="Power Factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_FREQUENCY,
        name="Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_TEMPERATURE,
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
)

SOLAR_SENSORS: tuple[BMWWallboxSensorDescription, ...] = (
    BMWWallboxSensorDescription(
        key=SENSOR_SOLAR_POWER,
        name="Solar Power Available",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
        is_solar=True,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_SOLAR_SURPLUS,
        name="Solar Surplus",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power-variant",
        is_solar=True,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_DYNAMIC_CURRENT_TARGET,
        name="Dynamic Current Target",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:current-ac",
        is_solar=True,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_DYNAMIC_MODE,
        name="Dynamic Charging Mode",
        icon="mdi:auto-mode",
        is_solar=True,
    ),
    BMWWallboxSensorDescription(
        key=SENSOR_CHARGING_SOURCE,
        name="Charging Source",
        icon="mdi:transmission-tower",
        is_solar=True,
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

    entities: list[BMWWallboxSensorBase] = []

    for desc in CHARGER_SENSORS:
        entities.append(BMWWallboxChargerSensor(entry.entry_id, desc, server, solar_controller))

    for desc in SOLAR_SENSORS:
        entities.append(BMWWallboxSolarSensor(entry.entry_id, desc, server, solar_controller))

    async_add_entities(entities)


class BMWWallboxSensorBase(BMWWallboxEntity, SensorEntity):
    """Base sensor entity."""

    def __init__(self, entry_id, description: BMWWallboxSensorDescription, server, solar_controller):
        super().__init__(entry_id, description.key, server, solar_controller)
        self.entity_description = description
        self._attr_name = description.name


class BMWWallboxChargerSensor(BMWWallboxSensorBase):
    """Sensor reading from charger state."""

    @property
    def native_value(self) -> Any:
        return self._charger_state.get_sensor_value(self.entity_description.key)

    @property
    def available(self) -> bool:
        return self._charger_state.connected or self.entity_description.key in (
            SENSOR_CONNECTOR_STATUS, SENSOR_CHARGING_STATE
        )


class BMWWallboxSolarSensor(BMWWallboxSensorBase):
    """Sensor reading from solar controller state."""

    @property
    def native_value(self) -> Any:
        sc = self._solar_controller
        key = self.entity_description.key
        if key == SENSOR_SOLAR_POWER:
            return round(sc.solar_power, 1)
        if key == SENSOR_SOLAR_SURPLUS:
            return round(sc.solar_surplus, 1)
        if key == SENSOR_DYNAMIC_CURRENT_TARGET:
            return round(sc.target_current, 1)
        if key == SENSOR_DYNAMIC_MODE:
            return sc.charging_mode
        if key == SENSOR_CHARGING_SOURCE:
            return sc.charging_source
        return None

    @property
    def available(self) -> bool:
        return True
