"""OCPP 2.0.1 Charger handler for BMW Wallbox Solar integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

try:
    from ocpp.routing import on
    from ocpp.v201 import ChargePoint as OcppChargePoint
    from ocpp.v201 import call_result
    from ocpp.v201.enums import (
        Action,
        AuthorizationStatusType,
        ChargingProfileKindType,
        ChargingProfilePurposeType,
        ChargingRateUnitType,
        ClearCachePretendType,
        GenericStatusType,
        IdTokenType,
        RegistrationStatusType,
        RequestStartStopStatusType,
        TransactionEventType,
    )
    from ocpp.v201.datatypes import (
        ChargingProfileType,
        ChargingScheduleType,
        ChargingSchedulePeriodType,
        IdTokenInfoType,
        IdTokenType as IdTokenDT,
    )
    OCPP_AVAILABLE = True
except ImportError:
    OCPP_AVAILABLE = False

from .const import (
    CONNECTOR_AVAILABLE,
    CONNECTOR_CHARGING,
    CONNECTOR_FINISHING,
    CONNECTOR_SUSPENDED_EV,
    CONNECTOR_SUSPENDED_EVSE,
    DOMAIN,
    SENSOR_CHARGING_STATE,
    SENSOR_CONNECTOR_STATUS,
    SENSOR_CURRENT_IMPORT,
    SENSOR_CURRENT_L1,
    SENSOR_CURRENT_L2,
    SENSOR_CURRENT_L3,
    SENSOR_CURRENT_OFFERED,
    SENSOR_ENERGY_SESSION,
    SENSOR_ENERGY_TOTAL,
    SENSOR_FREQUENCY,
    SENSOR_POWER,
    SENSOR_POWER_ACTIVE_IMPORT,
    SENSOR_POWER_FACTOR,
    SENSOR_POWER_REACTIVE_IMPORT,
    SENSOR_SESSION_DURATION,
    SENSOR_TEMPERATURE,
    SENSOR_TRANSACTION_ID,
    SENSOR_VOLTAGE,
    SENSOR_VOLTAGE_L1,
    SENSOR_VOLTAGE_L2,
    SENSOR_VOLTAGE_L3,
)

_LOGGER = logging.getLogger(__name__)


class ChargerState:
    """Holds all state for the connected wallbox."""

    def __init__(self) -> None:
        self.connected: bool = False
        self.charging: bool = False
        self.connector_status: str = CONNECTOR_AVAILABLE
        self.transaction_id: str | None = None

        # Meter values
        self.power: float = 0.0                     # W
        self.energy_total: float = 0.0              # kWh (lifetime)
        self.energy_session: float = 0.0            # Wh (current session)
        self.current_import: float = 0.0            # A (total)
        self.current_offered: float = 0.0           # A (limit offered to EV)
        self.voltage: float = 0.0                   # V (avg)
        self.current_l1: float = 0.0
        self.current_l2: float = 0.0
        self.current_l3: float = 0.0
        self.voltage_l1: float = 0.0
        self.voltage_l2: float = 0.0
        self.voltage_l3: float = 0.0
        self.power_active_import: float = 0.0
        self.power_reactive_import: float = 0.0
        self.power_factor: float = 1.0
        self.frequency: float = 50.0
        self.temperature: float | None = None

        # Session tracking
        self.session_start: datetime | None = None
        self.session_duration: int = 0              # seconds

        # Charging profile
        self.max_current: int = 16
        self.current_limit: int = 16

        # Callbacks
        self._update_callbacks: list = []

    def register_callback(self, callback) -> None:
        self._update_callbacks.append(callback)

    def unregister_callback(self, callback) -> None:
        self._update_callbacks.remove(callback)

    def notify(self) -> None:
        for cb in self._update_callbacks:
            cb()

    def get_sensor_value(self, sensor_key: str) -> Any:
        mapping = {
            SENSOR_POWER: self.power,
            SENSOR_ENERGY_TOTAL: self.energy_total,
            SENSOR_ENERGY_SESSION: self.energy_session,
            SENSOR_CURRENT_IMPORT: self.current_import,
            SENSOR_CURRENT_OFFERED: self.current_offered,
            SENSOR_VOLTAGE: self.voltage,
            SENSOR_CURRENT_L1: self.current_l1,
            SENSOR_CURRENT_L2: self.current_l2,
            SENSOR_CURRENT_L3: self.current_l3,
            SENSOR_VOLTAGE_L1: self.voltage_l1,
            SENSOR_VOLTAGE_L2: self.voltage_l2,
            SENSOR_VOLTAGE_L3: self.voltage_l3,
            SENSOR_POWER_ACTIVE_IMPORT: self.power_active_import,
            SENSOR_POWER_REACTIVE_IMPORT: self.power_reactive_import,
            SENSOR_POWER_FACTOR: self.power_factor,
            SENSOR_FREQUENCY: self.frequency,
            SENSOR_TEMPERATURE: self.temperature,
            SENSOR_CHARGING_STATE: self.connector_status,
            SENSOR_CONNECTOR_STATUS: self.connector_status,
            SENSOR_TRANSACTION_ID: self.transaction_id,
            SENSOR_SESSION_DURATION: self.session_duration,
        }
        return mapping.get(sensor_key)


if OCPP_AVAILABLE:
    class BMWWallboxChargePoint(OcppChargePoint):
        """OCPP 2.0.1 Charge Point handler for BMW Wallbox."""

        def __init__(self, id: str, connection, state: ChargerState, rfid_token: str | None = None):
            super().__init__(id, connection)
            self._state = state
            self._rfid_token = rfid_token
            self._state.connected = True
            _LOGGER.info("BMW Wallbox connected: %s", id)

        @on(Action.BootNotification)
        def on_boot_notification(self, charging_station, reason, **kwargs):
            _LOGGER.info("BootNotification from %s: %s", self.id, charging_station)
            self._state.notify()
            return call_result.BootNotification(
                current_time=datetime.now(timezone.utc).isoformat(),
                interval=300,
                status=RegistrationStatusType.accepted,
            )

        @on(Action.Heartbeat)
        def on_heartbeat(self, **kwargs):
            return call_result.Heartbeat(
                current_time=datetime.now(timezone.utc).isoformat()
            )

        @on(Action.StatusNotification)
        def on_status_notification(self, timestamp, connector_status, evse_id, connector_id, **kwargs):
            _LOGGER.debug("StatusNotification: evse=%s connector=%s status=%s", evse_id, connector_id, connector_status)
            self._state.connector_status = connector_status
            self._state.charging = connector_status in [
                CONNECTOR_CHARGING,
                CONNECTOR_SUSPENDED_EV,
                CONNECTOR_SUSPENDED_EVSE,
            ]
            if connector_status == CONNECTOR_FINISHING:
                self._state.session_duration = 0
                self._state.session_start = None
            self._state.notify()
            return call_result.StatusNotification()

        @on(Action.TransactionEvent)
        def on_transaction_event(self, event_type, timestamp, trigger_reason, seq_no, transaction_info, **kwargs):
            _LOGGER.debug("TransactionEvent: type=%s trigger=%s", event_type, trigger_reason)
            tx_id = transaction_info.get("transaction_id") if isinstance(transaction_info, dict) else getattr(transaction_info, "transaction_id", None)

            if event_type == TransactionEventType.started:
                self._state.transaction_id = tx_id
                self._state.energy_session = 0.0
                self._state.session_start = datetime.now(timezone.utc)
                self._state.charging = True

            elif event_type == TransactionEventType.ended:
                self._state.charging = False
                self._state.transaction_id = None
                self._state.session_start = None

            # Parse meter values from transaction event
            meter_values = kwargs.get("meter_value", [])
            self._parse_meter_values(meter_values)

            self._state.notify()
            return call_result.TransactionEvent(
                id_token_info=IdTokenInfoType(status=AuthorizationStatusType.accepted)
            )

        @on(Action.MeterValues)
        def on_meter_values(self, evse_id, meter_value, **kwargs):
            self._parse_meter_values(meter_value)
            # Update session duration
            if self._state.session_start:
                elapsed = (datetime.now(timezone.utc) - self._state.session_start).seconds
                self._state.session_duration = elapsed
            self._state.notify()
            return call_result.MeterValues()

        @on(Action.Authorize)
        def on_authorize(self, id_token, **kwargs):
            token_value = id_token.get("id_token") if isinstance(id_token, dict) else getattr(id_token, "id_token", "")
            if self._rfid_token and token_value != self._rfid_token:
                status = AuthorizationStatusType.unknown
            else:
                status = AuthorizationStatusType.accepted
            return call_result.Authorize(
                id_token_info=IdTokenInfoType(status=status)
            )

        @on(Action.NotifyReport)
        def on_notify_report(self, request_id, generated_at, seq_no, report_data=None, **kwargs):
            return call_result.NotifyReport()

        @on(Action.NotifyEvent)
        def on_notify_event(self, generated_at, seq_no, event_data, **kwargs):
            return call_result.NotifyEvent()

        @on(Action.SecurityEventNotification)
        def on_security_event(self, type, timestamp, **kwargs):
            _LOGGER.warning("Security event: %s at %s", type, timestamp)
            return call_result.SecurityEventNotification()

        def _parse_meter_values(self, meter_values: list) -> None:
            """Parse OCPP 2.0.1 meter values into state."""
            if not meter_values:
                return
            for mv in meter_values:
                sampled = mv.get("sampled_value", []) if isinstance(mv, dict) else getattr(mv, "sampled_value", [])
                for sv in sampled:
                    if isinstance(sv, dict):
                        measurand = sv.get("measurand", "")
                        value = sv.get("value", 0)
                        phase = sv.get("phase", None)
                        unit = sv.get("unit_of_measure", {})
                        if isinstance(unit, dict):
                            unit_multiplier = unit.get("multiplier", 0)
                        else:
                            unit_multiplier = getattr(unit, "multiplier", 0)
                    else:
                        measurand = getattr(sv, "measurand", "")
                        value = getattr(sv, "value", 0)
                        phase = getattr(sv, "phase", None)
                        unit_of_measure = getattr(sv, "unit_of_measure", None)
                        unit_multiplier = getattr(unit_of_measure, "multiplier", 0) if unit_of_measure else 0

                    try:
                        numeric = float(value) * (10 ** unit_multiplier)
                    except (ValueError, TypeError):
                        continue

                    self._assign_measurand(measurand, phase, numeric)

        def _assign_measurand(self, measurand: str, phase, value: float) -> None:
            """Map OCPP measurand string to state field."""
            m = measurand.lower() if measurand else ""

            if "energy.active.import" in m:
                if phase is None:
                    self._state.energy_total = round(value / 1000, 3)  # Wh -> kWh
                    self._state.energy_session = value  # Wh, set on session
            elif "power.active.import" in m:
                if phase is None:
                    self._state.power = round(value, 1)
                    self._state.power_active_import = self._state.power
            elif "power.reactive.import" in m:
                self._state.power_reactive_import = round(value, 1)
            elif "current.import" in m:
                if phase is None:
                    self._state.current_import = round(value, 2)
                elif "l1" in str(phase).lower():
                    self._state.current_l1 = round(value, 2)
                elif "l2" in str(phase).lower():
                    self._state.current_l2 = round(value, 2)
                elif "l3" in str(phase).lower():
                    self._state.current_l3 = round(value, 2)
            elif "current.offered" in m:
                self._state.current_offered = round(value, 2)
            elif "voltage" in m:
                if phase is None:
                    self._state.voltage = round(value, 1)
                elif "l1" in str(phase).lower():
                    self._state.voltage_l1 = round(value, 1)
                elif "l2" in str(phase).lower():
                    self._state.voltage_l2 = round(value, 1)
                elif "l3" in str(phase).lower():
                    self._state.voltage_l3 = round(value, 1)
            elif "power.factor" in m:
                self._state.power_factor = round(value, 3)
            elif "frequency" in m:
                self._state.frequency = round(value, 2)
            elif "temperature" in m:
                self._state.temperature = round(value, 1)

        # ── Commands sent TO the wallbox ─────────────────────────────────────

        async def set_charging_profile(self, current_limit_amps: float) -> bool:
            """Send a SetChargingProfile to limit charging current."""
            if not OCPP_AVAILABLE:
                return False
            try:
                from ocpp.v201 import call as v201_call
                period = ChargingSchedulePeriodType(
                    start_period=0,
                    limit=current_limit_amps,
                )
                schedule = ChargingScheduleType(
                    id=1,
                    charging_rate_unit=ChargingRateUnitType.amps,
                    charging_schedule_period=[period],
                )
                profile = ChargingProfileType(
                    id=1,
                    stack_level=0,
                    charging_profile_purpose=ChargingProfilePurposeType.tx_default_profile,
                    charging_profile_kind=ChargingProfileKindType.relative,
                    charging_schedule=[schedule],
                )
                request = v201_call.SetChargingProfile(
                    evse_id=1,
                    charging_profile=profile,
                )
                response = await self.call(request)
                ok = response.status == GenericStatusType.accepted
                if ok:
                    self._state.current_limit = int(current_limit_amps)
                    self._state.current_offered = current_limit_amps
                    self._state.notify()
                return ok
            except Exception as exc:
                _LOGGER.error("Failed to set charging profile: %s", exc)
                return False

        async def remote_start_transaction(self, id_token: str | None = None) -> bool:
            """Send RequestStartTransaction."""
            try:
                from ocpp.v201 import call as v201_call
                token = id_token or self._rfid_token or "HA_START"
                request = v201_call.RequestStartTransaction(
                    evse_id=1,
                    id_token=IdTokenDT(id_token=token, type=IdTokenType.central),
                )
                response = await self.call(request)
                return response.status == RequestStartStopStatusType.accepted
            except Exception as exc:
                _LOGGER.error("Failed to start transaction: %s", exc)
                return False

        async def remote_stop_transaction(self) -> bool:
            """Send RequestStopTransaction."""
            if not self._state.transaction_id:
                return False
            try:
                from ocpp.v201 import call as v201_call
                request = v201_call.RequestStopTransaction(
                    transaction_id=self._state.transaction_id,
                )
                response = await self.call(request)
                return response.status == RequestStartStopStatusType.accepted
            except Exception as exc:
                _LOGGER.error("Failed to stop transaction: %s", exc)
                return False

        async def clear_cache(self) -> bool:
            """Clear the charger's authorization cache."""
            try:
                from ocpp.v201 import call as v201_call
                request = v201_call.ClearCache()
                response = await self.call(request)
                return response.status == ClearCachePretendType.accepted
            except Exception as exc:
                _LOGGER.error("Failed to clear cache: %s", exc)
                return False

        def disconnect(self) -> None:
            self._state.connected = False
            self._state.charging = False
            self._state.connector_status = CONNECTOR_AVAILABLE
            self._state.transaction_id = None
            self._state.notify()

else:
    # Stub when ocpp library is not installed
    class BMWWallboxChargePoint:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise RuntimeError("ocpp library not installed")
