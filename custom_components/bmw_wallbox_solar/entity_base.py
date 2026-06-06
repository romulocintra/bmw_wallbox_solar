"""Base entity for BMW Wallbox Solar integration."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN


class BMWWallboxEntity(Entity):
    """Base entity providing device info and update subscriptions."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry_id: str, unique_suffix: str, server, solar_controller) -> None:
        self._entry_id = entry_id
        self._server = server
        self._solar_controller = solar_controller
        self._attr_unique_id = f"{entry_id}_{unique_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="BMW Wallbox Solar",
            manufacturer="Delta Electronics / BMW",
            model="EIAW-E22KTSE6B04 (OCPP 2.0.1)",
            sw_version="1.0.0",
        )

    @property
    def _charger_state(self):
        return self._server.state

    @property
    def _charge_point(self):
        return self._server.charge_point

    def _handle_update(self) -> None:
        self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        self._charger_state.register_callback(self._handle_update)
        self._solar_controller.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        self._charger_state.unregister_callback(self._handle_update)
        self._solar_controller.unregister_callback(self._handle_update)
