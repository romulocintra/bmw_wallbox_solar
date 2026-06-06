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
    SSL_MODES,
)

SSL_MODE_LABELS = {
    SSL_MODE_NONE: "None — plain ws:// (use reverse proxy for TLS)",
    SSL_MODE_AUTO: "Auto — reuse Home Assistant's existing certificate",
    SSL_MODE_MANUAL: "Manual — specify cert and key file paths",
}


class BMWWallboxSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BMW Wallbox Solar."""

    VERSION = 1
    _data: dict = {}

    async def async_step_user(self, user_input=None):
        """Step 1: OCPP connection basics + SSL mode."""
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            ssl_mode = user_input.get(CONF_SSL_MODE, SSL_MODE_AUTO)
            if ssl_mode == SSL_MODE_MANUAL:
                return await self.async_step_ssl_manual()
            # Auto or None — go straight to solar config
            return await self.async_step_solar()

        schema = vol.Schema({
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Optional(CONF_CHARGE_POINT_ID, default=""): str,
            vol.Optional(CONF_RFID_TOKEN, default=""): str,
            vol.Required(CONF_MAX_CURRENT, default=DEFAULT_MAX_CURRENT): vol.All(
                int, vol.Range(min=6, max=32)
            ),
            vol.Required(CONF_SSL_MODE, default=SSL_MODE_AUTO): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": k, "label": v}
                        for k, v in SSL_MODE_LABELS.items()
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        })
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "info": (
                    "BMW/Mini wallboxes require WSS. Choose 'Auto' to reuse "
                    "your HA certificate, 'Manual' to specify paths, or 'None' "
                    "if you have a reverse proxy (Nginx/Caddy) handling TLS."
                )
            },
        )

    async def async_step_ssl_manual(self, user_input=None):
        """Step 1b: collect cert/key paths when manual SSL is selected."""
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_solar()

        schema = vol.Schema({
            vol.Required(CONF_SSL_CERT, default="/ssl/fullchain.pem"): str,
            vol.Required(CONF_SSL_KEY, default="/ssl/privkey.pem"): str,
        })
        return self.async_show_form(
            step_id="ssl_manual",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_solar(self, user_input=None):
        """Step 2: optional solar entity wiring."""
        if user_input is not None:
            self._data.update(user_input)
            await self.async_set_unique_id(
                self._data.get(CONF_CHARGE_POINT_ID)
                or f"bmw_wallbox_{self._data[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            cp_id = self._data.get(CONF_CHARGE_POINT_ID) or f"port {self._data[CONF_PORT]}"
            return self.async_create_entry(
                title=f"BMW Wallbox Solar ({cp_id})",
                data=self._data,
            )

        schema = vol.Schema({
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
            vol.Required(CONF_GRID_EXPORT_LIMIT, default=DEFAULT_GRID_EXPORT_LIMIT): vol.All(
                float, vol.Range(min=0)
            ),
        })
        return self.async_show_form(
            step_id="solar",
            data_schema=schema,
            description_placeholders={
                "hint": (
                    "Link your inverter sensors (Solarman/Deye, Sunsynk, Huawei Solar, etc.). "
                    "All fields are optional — skip any you don't have."
                )
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BMWWallboxSolarOptionsFlow(config_entry)


class BMWWallboxSolarOptionsFlow(config_entries.OptionsFlow):
    """Options flow to reconfigure after setup."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._config_entry.data, **self._config_entry.options}

        schema = vol.Schema({
            vol.Required(CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Required(CONF_MAX_CURRENT, default=current.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)): vol.All(
                int, vol.Range(min=6, max=32)
            ),
            vol.Required(CONF_SSL_MODE, default=current.get(CONF_SSL_MODE, SSL_MODE_AUTO)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[{"value": k, "label": v} for k, v in SSL_MODE_LABELS.items()],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(CONF_SSL_CERT, default=current.get(CONF_SSL_CERT, "")): str,
            vol.Optional(CONF_SSL_KEY, default=current.get(CONF_SSL_KEY, "")): str,
            vol.Optional(CONF_SOLAR_POWER_ENTITY, default=current.get(CONF_SOLAR_POWER_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_GRID_POWER_ENTITY, default=current.get(CONF_GRID_POWER_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_HOUSE_LOAD_ENTITY, default=current.get(CONF_HOUSE_LOAD_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_BATTERY_SOC_ENTITY, default=current.get(CONF_BATTERY_SOC_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_BATTERY_POWER_ENTITY, default=current.get(CONF_BATTERY_POWER_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_MIN_CHARGE_CURRENT, default=current.get(CONF_MIN_CHARGE_CURRENT, DEFAULT_MIN_CURRENT)): vol.All(
                int, vol.Range(min=6, max=16)
            ),
            vol.Required(CONF_BATTERY_RESERVE_SOC, default=current.get(CONF_BATTERY_RESERVE_SOC, DEFAULT_BATTERY_RESERVE_SOC)): vol.All(
                int, vol.Range(min=0, max=100)
            ),
            vol.Required(CONF_GRID_EXPORT_LIMIT, default=current.get(CONF_GRID_EXPORT_LIMIT, DEFAULT_GRID_EXPORT_LIMIT)): vol.All(
                float, vol.Range(min=0)
            ),
        })

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
