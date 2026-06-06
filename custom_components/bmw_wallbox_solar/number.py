"""Number platform for BMW Wallbox Solar integration."""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_SERVER,
    DATA_SOLAR_CONTROLLER,
    DOMAIN,
    NUMBER_BATTERY_RESERVE_SOC,
    NUMBER_CURRENT_LIMIT,
    NUMBER_MIN_CHARGE_CURRENT,
)
from .entity_base import BMWWallboxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    server = data[DATA_SERVER]
    sc = data[DATA_SOLAR_CONTROLLER]

    async_add_entities([
        CurrentLimitNumber(entry.entry_id, server, sc),
        MinChargeCurrentNumber(entry.entry_id, server, sc),
        BatteryReserveSocNumber(entry.entry_id, server, sc),
    ])


class CurrentLimitNumber(BMWWallboxEntity, NumberEntity):
    """Manual current limit slider (overrides dynamic control when not in auto)."""

    _attr_name = "Current Limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 32
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:current-ac"

    def __init__(self, entry_id, server, solar_controller):
        super().__init__(entry_id, NUMBER_CURRENT_LIMIT, server, solar_controller)

    @property
    def native_value(self) -> float:
        return float(self._charger_state.current_limit)

    async def async_set_native_value(self, value: float) -> None:
        self._charger_state.current_limit = int(value)
        if self._charge_point:
            await self._charge_point.set_charging_profile(value)


class MinChargeCurrentNumber(BMWWallboxEntity, NumberEntity):
    """Minimum charge current for solar mode."""

    _attr_name = "Minimum Charge Current"
    _attr_native_min_value = 6
    _attr_native_max_value = 16
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:current-ac"

    def __init__(self, entry_id, server, solar_controller):
        super().__init__(entry_id, NUMBER_MIN_CHARGE_CURRENT, server, solar_controller)

    @property
    def native_value(self) -> float:
        return float(self._solar_controller.min_charge_current)

    async def async_set_native_value(self, value: float) -> None:
        self._solar_controller.min_charge_current = int(value)
        await self._solar_controller.async_recalculate_and_apply(self._charge_point)


class BatteryReserveSocNumber(BMWWallboxEntity, NumberEntity):
    """Battery SOC reserve — don't use battery for EV charging below this."""

    _attr_name = "Battery Reserve SOC"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = "%"
    _attr_device_class = NumberDeviceClass.BATTERY
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:battery-lock"

    def __init__(self, entry_id, server, solar_controller):
        super().__init__(entry_id, NUMBER_BATTERY_RESERVE_SOC, server, solar_controller)

    @property
    def native_value(self) -> float:
        return float(self._solar_controller.battery_reserve_soc)

    async def async_set_native_value(self, value: float) -> None:
        self._solar_controller.battery_reserve_soc = int(value)
        await self._solar_controller.async_recalculate_and_apply(self._charge_point)
