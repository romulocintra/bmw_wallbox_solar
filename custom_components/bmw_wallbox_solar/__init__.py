"""BMW Wallbox Solar Dynamic Charging - Home Assistant Integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CHARGE_POINT_ID,
    CONF_DYNAMIC_CHARGING_ENABLED,
    CONF_GRID_EXPORT_LIMIT,
    CONF_MAX_CURRENT,
    CONF_MIN_CHARGE_CURRENT,
    CONF_PORT,
    CONF_RFID_TOKEN,
    CONF_SSL_CERT,
    CONF_SSL_KEY,
    CONF_SSL_MODE,
    CONF_SOLAR_POWER_ENTITY,
    CONF_GRID_POWER_ENTITY,
    CONF_HOUSE_LOAD_ENTITY,
    CONF_BATTERY_SOC_ENTITY,
    CONF_BATTERY_POWER_ENTITY,
    CONF_BATTERY_RESERVE_SOC,
    DATA_SERVER,
    DATA_SOLAR_CONTROLLER,
    DEFAULT_BATTERY_RESERVE_SOC,
    DEFAULT_GRID_EXPORT_LIMIT,
    DEFAULT_MAX_CURRENT,
    DEFAULT_MIN_CURRENT,
    DEFAULT_PORT,
    DOMAIN,
    SSL_MODE_AUTO,
)
from .server import OCPPServer
from .solar_controller import SolarController

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BMW Wallbox Solar from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Build OCPP server
    server = OCPPServer(
        port=entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, DEFAULT_PORT)),
        ssl_mode=entry.options.get(CONF_SSL_MODE, entry.data.get(CONF_SSL_MODE, SSL_MODE_AUTO)),
        ssl_cert=entry.data.get(CONF_SSL_CERT),
        ssl_key=entry.data.get(CONF_SSL_KEY),
        expected_charge_point_id=entry.data.get(CONF_CHARGE_POINT_ID),
        rfid_token=entry.data.get(CONF_RFID_TOKEN),
    )

    await server.async_start()

    # Build solar controller
    solar_controller = SolarController(
        hass=hass,
        charger_state=server.state,
        solar_power_entity=entry.options.get(CONF_SOLAR_POWER_ENTITY, entry.data.get(CONF_SOLAR_POWER_ENTITY)),
        grid_power_entity=entry.options.get(CONF_GRID_POWER_ENTITY, entry.data.get(CONF_GRID_POWER_ENTITY)),
        house_load_entity=entry.options.get(CONF_HOUSE_LOAD_ENTITY, entry.data.get(CONF_HOUSE_LOAD_ENTITY)),
        battery_soc_entity=entry.options.get(CONF_BATTERY_SOC_ENTITY, entry.data.get(CONF_BATTERY_SOC_ENTITY)),
        battery_power_entity=entry.options.get(CONF_BATTERY_POWER_ENTITY, entry.data.get(CONF_BATTERY_POWER_ENTITY)),
        max_current=entry.options.get(CONF_MAX_CURRENT, entry.data.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)),
        min_charge_current=entry.options.get(CONF_MIN_CHARGE_CURRENT, entry.data.get(CONF_MIN_CHARGE_CURRENT, DEFAULT_MIN_CURRENT)),
        battery_reserve_soc=entry.options.get(CONF_BATTERY_RESERVE_SOC, entry.data.get(CONF_BATTERY_RESERVE_SOC, DEFAULT_BATTERY_RESERVE_SOC)),
        grid_export_limit=entry.options.get(CONF_GRID_EXPORT_LIMIT, entry.data.get(CONF_GRID_EXPORT_LIMIT, DEFAULT_GRID_EXPORT_LIMIT)),
    )

    solar_controller.async_start()

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_SERVER: server,
        DATA_SOLAR_CONTROLLER: solar_controller,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        server: OCPPServer = data[DATA_SERVER]
        solar_controller: SolarController = data[DATA_SOLAR_CONTROLLER]
        solar_controller.async_stop()
        await server.async_stop()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
