"""Config flow for BMW Wallbox Solar Dynamic Charging."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BATTERY_POWER_ENTITY,
    CONF_BATTERY_RESERVE_SOC,
    CONF_BATTERY_SOC_ENTITY,
    CONF_CHARGE_POINT_ID,
    CONF_GRID_EXPORT_LIMIT,
    CONF_GRID_POWER_ENTITY,
    CONF_HOUSE_LOAD_ENTITY,
    CONF_MAX_CURRENT,
    CONF_MIN_CHARGE_CURRENT,
    CONF_PORT,
    CONF_RFID_TOKEN,
    CONF_SOLAR_POWER_ENTITY,
    CONF_SSL_CERT,
    CONF_SSL_KEY,
    CONF_SSL_MODE,
    DEFAULT_BATTERY_RESERVE_SOC,
    DEFAULT_GRID_EXPORT_LIMIT,
    DEFAULT_MAX_CURRENT,
    DEFAULT_MIN_CURRENT,
    DEFAULT_PORT,
    DOMAIN,
    SSL_MODE_AUTO,
    SSL_MODE_MANUAL,
    SSL_MODE_NONE,
)

SSL_MODE_OPTIONS = [
    selector.SelectOptionDict(
        value=SSL_MODE_NONE,
        label="None — plain ws:// (use a reverse proxy for TLS)",
    ),
    selector.SelectOptionDict(
        value=SSL_MODE_AUTO,
        label="Auto — reuse Home Assistant's existing certificate",
    ),
    selector.SelectOptionDict(
        value=SSL_MODE_MANUAL,
        label="Manual — specify cert and key file paths",
    ),
]


class BMWWallboxSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BMW Wallbox Solar."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise — use instance variable, not class variable."""
        self._data: dict = {}

    # ── Step 1: port, CP ID, SSL mode ────────────────────────────────────────

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            if user_input.get(CONF_SSL_MODE) == SSL_MODE_MANUAL:
                return await self.async_step_ssl_manual()
            return await self.async_step_solar()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_CHARGE_POINT_ID, default=""): str,
                vol.Optional(CONF_RFID_TOKEN, default=""): str,
                vol.Required(CONF_MAX_CURRENT, default=DEFAULT_MAX_CURRENT): vol.All(
                    int, vol.Range(min=6, max=32)
                ),
                vol.Required(CONF_SSL_MODE, default=SSL_MODE_AUTO): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=SSL_MODE_OPTIONS)
                ),
            }),
        )

    # ── Step 1b: manual cert paths ───────────────────────────────────────────

    async def async_step_ssl_manual(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_solar()

        return self.async_show_form(
            step_id="ssl_manual",
            data_schema=vol.Schema({
                vol.Required(CONF_SSL_CERT, default="/ssl/fullchain.pem"): str,
                vol.Required(CONF_SSL_KEY, default="/ssl/privkey.pem"): str,
            }),
        )

    # ── Step 2: solar entity wiring ──────────────────────────────────────────

    async def async_step_solar(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            cp_id = self._data.get(CONF_CHARGE_POINT_ID) or f"bmw_wallbox_{self._data[CONF_PORT]}"
            await self.async_set_unique_id(cp_id)
            self._abort_if_unique_id_configured()
            title = f"BMW Wallbox ({self._data.get(CONF_CHARGE_POINT_ID) or f'port {self._data[CONF_PORT]}'})"
            return self.async_create_entry(title=title, data=self._data)

        return self.async_show_form(
            step_id="solar",
            data_schema=vol.Schema({
                vol.Optional(CONF_SOLAR_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_GRID_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_HOUSE_LOAD_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_BATTERY_SOC_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_BATTERY_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_MIN_CHARGE_CURRENT, default=DEFAULT_MIN_CURRENT): vol.All(
                    int, vol.Range(min=6, max=16)
                ),
                vol.Required(CONF_BATTERY_RESERVE_SOC, default=DEFAULT_BATTERY_RESERVE_SOC): vol.All(
                    int, vol.Range(min=0, max=100)
                ),
                vol.Required(CONF_GRID_EXPORT_LIMIT, default=float(DEFAULT_GRID_EXPORT_LIMIT)): vol.All(
                    vol.Coerce(float), vol.Range(min=0)
                ),
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BMWWallboxSolarOptionsFlow(config_entry)


class BMWWallboxSolarOptionsFlow(config_entries.OptionsFlow):
    """Options flow — reconfigure after initial setup."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._config_entry.data, **self._config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Required(CONF_MAX_CURRENT, default=current.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)): vol.All(
                    int, vol.Range(min=6, max=32)
                ),
                vol.Required(CONF_SSL_MODE, default=current.get(CONF_SSL_MODE, SSL_MODE_AUTO)): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=SSL_MODE_OPTIONS)
                ),
                vol.Optional(CONF_SSL_CERT, default=current.get(CONF_SSL_CERT, "")): str,
                vol.Optional(CONF_SSL_KEY, default=current.get(CONF_SSL_KEY, "")): str,
                vol.Optional(CONF_SOLAR_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_GRID_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_HOUSE_LOAD_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_BATTERY_SOC_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_BATTERY_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_MIN_CHARGE_CURRENT, default=current.get(CONF_MIN_CHARGE_CURRENT, DEFAULT_MIN_CURRENT)): vol.All(
                    int, vol.Range(min=6, max=16)
                ),
                vol.Required(CONF_BATTERY_RESERVE_SOC, default=current.get(CONF_BATTERY_RESERVE_SOC, DEFAULT_BATTERY_RESERVE_SOC)): vol.All(
                    int, vol.Range(min=0, max=100)
                ),
                vol.Required(CONF_GRID_EXPORT_LIMIT, default=float(current.get(CONF_GRID_EXPORT_LIMIT, DEFAULT_GRID_EXPORT_LIMIT))): vol.All(
                    vol.Coerce(float), vol.Range(min=0)
                ),
            }),
        )
