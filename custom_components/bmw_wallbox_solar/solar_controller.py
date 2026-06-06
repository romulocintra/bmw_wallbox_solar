"""Solar dynamic charging controller.

This module reads solar production, grid power, house load, and battery SOC
from other HA entities (e.g. Solarman / Deye integration) and calculates the
optimal charge current for the BMW Wallbox.

Entity naming follows the Solarman/Deye convention:
  sensor.deye_solar_power            → total PV generation (W)
  sensor.deye_grid_power             → grid import/export (W, negative = export)
  sensor.deye_load_power             → house consumption (W)
  sensor.deye_battery_soc            → battery state of charge (%)
  sensor.deye_battery_power          → battery charge/discharge (W)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .const import (
    CHARGING_MODE_FAST,
    CHARGING_MODE_OFF,
    CHARGING_MODE_SOLAR_GRID,
    CHARGING_MODE_SOLAR_ONLY,
    DEFAULT_MIN_CURRENT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Voltage assumption for current calculation (single/three phase detection)
ASSUMED_VOLTAGE = 230.0
PHASES = 3  # BMW wallbox is 3-phase 22kW


class SolarController:
    """Calculates dynamic EV charging current from solar + grid data."""

    def __init__(
        self,
        hass: HomeAssistant,
        charger_state,
        solar_power_entity: str | None,
        grid_power_entity: str | None,
        house_load_entity: str | None,
        battery_soc_entity: str | None,
        battery_power_entity: str | None,
        max_current: int,
        min_charge_current: int,
        battery_reserve_soc: int,
        grid_export_limit: float,
    ) -> None:
        self._hass = hass
        self._charger_state = charger_state
        self._solar_entity = solar_power_entity
        self._grid_entity = grid_power_entity
        self._house_load_entity = house_load_entity
        self._battery_soc_entity = battery_soc_entity
        self._battery_power_entity = battery_power_entity

        self.max_current: int = max_current
        self.min_charge_current: int = min_charge_current
        self.battery_reserve_soc: int = battery_reserve_soc
        self.grid_export_limit: float = grid_export_limit

        # Dynamic mode state
        self.charging_mode: str = CHARGING_MODE_SOLAR_GRID
        self.dynamic_enabled: bool = True
        self.target_current: float = 0.0

        # Live readings from entities
        self.solar_power: float = 0.0       # W — PV generation
        self.grid_power: float = 0.0        # W — positive = import, negative = export
        self.house_load: float = 0.0        # W — home consumption (excl. charger)
        self.battery_soc: float | None = None
        self.battery_power: float = 0.0     # W — positive = charging, neg = discharging
        self.solar_surplus: float = 0.0     # W — power available for EV
        self.charging_source: str = "none"  # "solar", "grid", "mixed", "none"

        # Update callbacks for HA entities
        self._update_callbacks: list = []
        self._unsub_listeners: list = []
        self._unsub_timer = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    @callback
    def async_start(self) -> None:
        """Start listening to source entity state changes."""
        entities = [e for e in [
            self._solar_entity,
            self._grid_entity,
            self._house_load_entity,
            self._battery_soc_entity,
            self._battery_power_entity,
        ] if e]

        if entities:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self._hass, entities, self._on_source_entity_change
                )
            )

        # Also run on a timer as a safety net
        self._unsub_timer = async_track_time_interval(
            self._hass,
            self._on_timer_update,
            timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

        # Read initial values
        self._read_all_entities()

    def async_stop(self) -> None:
        """Stop all listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    # ── Callbacks ────────────────────────────────────────────────────────────

    def register_callback(self, callback) -> None:
        self._update_callbacks.append(callback)

    def unregister_callback(self, callback) -> None:
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)

    def _notify(self) -> None:
        for cb in self._update_callbacks:
            cb()

    @callback
    def _on_source_entity_change(self, event) -> None:
        self._read_all_entities()
        self._calculate()
        self._notify()

    @callback
    def _on_timer_update(self, now) -> None:
        self._read_all_entities()
        self._calculate()
        self._notify()

    # ── Entity reading ────────────────────────────────────────────────────────

    def _get_float(self, entity_id: str | None, default: float = 0.0) -> float:
        if not entity_id:
            return default
        state = self._hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown", ""):
            return default
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return default

    def _read_all_entities(self) -> None:
        self.solar_power = max(0.0, self._get_float(self._solar_entity))
        # Grid: negative = exporting, positive = importing (Deye convention)
        self.grid_power = self._get_float(self._grid_entity)
        self.house_load = max(0.0, self._get_float(self._house_load_entity))
        self.battery_power = self._get_float(self._battery_power_entity)
        soc_raw = self._get_float(self._battery_soc_entity, default=-1.0)
        self.battery_soc = soc_raw if soc_raw >= 0 else None

    # ── Core calculation ─────────────────────────────────────────────────────

    def _calculate(self) -> None:
        """Determine the optimal charge current and update target_current."""
        if not self.dynamic_enabled or self.charging_mode == CHARGING_MODE_OFF:
            self.target_current = 0.0
            self.charging_source = "none"
            self.solar_surplus = 0.0
            return

        if self.charging_mode == CHARGING_MODE_FAST:
            self.target_current = self.max_current
            self.charging_source = "grid"
            self.solar_surplus = self.solar_power
            return

        # Estimate current charger draw (W)
        charger_draw = self._charger_state.power if self._charger_state.charging else 0.0

        # Available solar surplus = PV - house load (excl. charger) - battery charge
        # grid_power negative means we are exporting, which is surplus
        # Compute surplus as: solar - house_load + (charger draw already exported)
        surplus_w = self.solar_power - self.house_load - max(0.0, self.battery_power)
        # Add back the current charger draw (it's part of our surplus budget)
        surplus_w += charger_draw
        self.solar_surplus = surplus_w

        # Respect battery reserve: if SOC is below reserve and battery is discharging, be conservative
        battery_reserve_active = (
            self.battery_soc is not None
            and self.battery_soc < self.battery_reserve_soc
            and self.battery_power < 0  # discharging
        )

        if self.charging_mode == CHARGING_MODE_SOLAR_ONLY:
            if battery_reserve_active:
                # Not enough battery headroom — stop
                available_w = 0.0
            else:
                available_w = max(0.0, surplus_w)
            self.charging_source = "solar" if available_w > 0 else "none"

        elif self.charging_mode == CHARGING_MODE_SOLAR_GRID:
            # Allow grid import up to grid_export_limit (W)
            grid_headroom = self.grid_export_limit if self.grid_export_limit > 0 else float("inf")
            # Available = surplus + allowed grid import
            available_w = surplus_w + grid_headroom
            if battery_reserve_active:
                available_w = min(available_w, surplus_w)  # no extra grid for battery safety

            if available_w <= 0:
                available_w = 0.0
                self.charging_source = "none"
            elif surplus_w >= available_w * 0.9:
                self.charging_source = "solar"
            elif surplus_w > 0:
                self.charging_source = "mixed"
            else:
                self.charging_source = "grid"
        else:
            available_w = 0.0
            self.charging_source = "none"

        # Convert watts to amps (3-phase)
        raw_amps = available_w / (ASSUMED_VOLTAGE * PHASES)

        # Clamp to allowed range
        if raw_amps < self.min_charge_current:
            # Below minimum — either pause or hold at min
            if self.charging_mode == CHARGING_MODE_SOLAR_ONLY:
                target = 0.0  # pause in solar-only
            else:
                target = self.min_charge_current if raw_amps > (self.min_charge_current * 0.5) else 0.0
        else:
            target = min(raw_amps, self.max_current)

        self.target_current = round(target, 1)
        _LOGGER.debug(
            "SolarController: solar=%.0fW surplus=%.0fW target=%.1fA mode=%s source=%s",
            self.solar_power, surplus_w, self.target_current, self.charging_mode, self.charging_source,
        )

    # ── Public API ───────────────────────────────────────────────────────────

    async def async_apply_to_charger(self, charge_point) -> None:
        """Push the current target_current to the wallbox via OCPP."""
        if charge_point is None:
            return
        if not self._charger_state.charging:
            return
        new_limit = int(self.target_current)
        if new_limit == 0:
            await charge_point.remote_stop_transaction()
        elif new_limit != self._charger_state.current_limit:
            await charge_point.set_charging_profile(new_limit)

    async def async_recalculate_and_apply(self, charge_point) -> None:
        """Force recalculation and apply immediately."""
        self._read_all_entities()
        self._calculate()
        await self.async_apply_to_charger(charge_point)
        self._notify()
