"""Switch platform for BMW Wallbox Solar integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_SERVER, DATA_SOLAR_CONTROLLER, DOMAIN, SWITCH_DYNAMIC_CHARGING
from .entity_base import BMWWallboxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DynamicChargingSwitch(entry.entry_id, data[DATA_SERVER], data[DATA_SOLAR_CONTROLLER])
    ])


class DynamicChargingSwitch(BMWWallboxEntity, SwitchEntity):
    """Enable or disable dynamic solar charging control."""

    _attr_name = "Dynamic Charging"
    _attr_icon = "mdi:solar-power-variant-outline"

    def __init__(self, entry_id, server, solar_controller):
        super().__init__(entry_id, SWITCH_DYNAMIC_CHARGING, server, solar_controller)

    @property
    def is_on(self) -> bool:
        return self._solar_controller.dynamic_enabled

    async def async_turn_on(self, **kwargs) -> None:
        self._solar_controller.dynamic_enabled = True
        await self._solar_controller.async_recalculate_and_apply(self._charge_point)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._solar_controller.dynamic_enabled = False
        self.async_write_ha_state()
