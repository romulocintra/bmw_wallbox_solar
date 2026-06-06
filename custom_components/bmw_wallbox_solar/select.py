"""Select platform for BMW Wallbox Solar integration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CHARGING_MODE_FAST,
    CHARGING_MODE_OFF,
    CHARGING_MODE_SOLAR_GRID,
    CHARGING_MODE_SOLAR_ONLY,
    CHARGING_MODES,
    DATA_SERVER,
    DATA_SOLAR_CONTROLLER,
    DOMAIN,
    SELECT_CHARGING_MODE,
)
from .entity_base import BMWWallboxEntity

MODE_LABELS = {
    CHARGING_MODE_FAST: "Fast (Max Power)",
    CHARGING_MODE_SOLAR_ONLY: "Solar Only",
    CHARGING_MODE_SOLAR_GRID: "Solar + Grid",
    CHARGING_MODE_OFF: "Off",
}
LABEL_TO_MODE = {v: k for k, v in MODE_LABELS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ChargingModeSelect(entry.entry_id, data[DATA_SERVER], data[DATA_SOLAR_CONTROLLER])
    ])


class ChargingModeSelect(BMWWallboxEntity, SelectEntity):
    """Select the dynamic charging mode."""

    _attr_name = "Charging Mode"
    _attr_icon = "mdi:car-electric"
    _attr_options = list(MODE_LABELS.values())

    def __init__(self, entry_id, server, solar_controller):
        super().__init__(entry_id, SELECT_CHARGING_MODE, server, solar_controller)

    @property
    def current_option(self) -> str:
        return MODE_LABELS.get(self._solar_controller.charging_mode, MODE_LABELS[CHARGING_MODE_SOLAR_GRID])

    async def async_select_option(self, option: str) -> None:
        mode = LABEL_TO_MODE.get(option, CHARGING_MODE_SOLAR_GRID)
        self._solar_controller.charging_mode = mode

        if mode == CHARGING_MODE_OFF and self._charge_point:
            await self._charge_point.remote_stop_transaction()
        elif mode == CHARGING_MODE_FAST:
            if self._charge_point and not self._charger_state.charging:
                await self._charge_point.remote_start_transaction()
            if self._charge_point:
                await self._charge_point.set_charging_profile(self._solar_controller.max_current)

        await self._solar_controller.async_recalculate_and_apply(self._charge_point)
