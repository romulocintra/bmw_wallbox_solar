"""Button platform for BMW Wallbox Solar integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_SERVER, DATA_SOLAR_CONTROLLER, DOMAIN
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
        StartChargingButton(entry.entry_id, server, sc),
        StopChargingButton(entry.entry_id, server, sc),
        ForceRecalculateButton(entry.entry_id, server, sc),
    ])


class StartChargingButton(BMWWallboxEntity, ButtonEntity):
    _attr_name = "Start Charging"
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, entry_id, server, sc):
        super().__init__(entry_id, "start_charging", server, sc)

    async def async_press(self) -> None:
        if self._charge_point:
            await self._charge_point.remote_start_transaction()


class StopChargingButton(BMWWallboxEntity, ButtonEntity):
    _attr_name = "Stop Charging"
    _attr_icon = "mdi:stop-circle-outline"

    def __init__(self, entry_id, server, sc):
        super().__init__(entry_id, "stop_charging", server, sc)

    async def async_press(self) -> None:
        if self._charge_point:
            await self._charge_point.remote_stop_transaction()


class ForceRecalculateButton(BMWWallboxEntity, ButtonEntity):
    """Immediately recalculate solar surplus and push new current limit."""

    _attr_name = "Recalculate Solar Charging"
    _attr_icon = "mdi:refresh"

    def __init__(self, entry_id, server, sc):
        super().__init__(entry_id, "force_recalculate", server, sc)

    async def async_press(self) -> None:
        await self._solar_controller.async_recalculate_and_apply(self._charge_point)
