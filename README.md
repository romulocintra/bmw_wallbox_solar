# BMW Wallbox Solar Dynamic Charging

A Home Assistant custom integration that:
1. Acts as an **OCPP 2.0.1 Central System (server)** for BMW/Mini/Delta Electronics wallboxes
2. Reads solar production, grid power, house load, and battery SOC from your inverter integration (e.g. **Solarman / Deye**)
3. Dynamically adjusts EV charge current in real time to maximize solar self-consumption

---

## Features

| Category | Details |
|---|---|
| Protocol | OCPP 2.0.1 over WebSocket Secure (WSS) |
| Sensors | 20+ — power, energy, per-phase V/A, temperature, solar surplus, charging source |
| Controls | Start/stop, current limit slider, charging mode, min current, battery reserve SOC |
| Solar modes | Fast, Solar Only, Solar + Grid, Off |
| Source entities | Compatible with any HA sensor — Solarman, Sunsynk, Huawei Solar, Fronius, SMA, etc. |
| Energy Dashboard | Full integration via `total_increasing` energy sensors |
| Local | No cloud required |

---

## Hardware

Tested with:
- **BMW Wallbox** (Delta Electronics EIAW-E22KTSE6B04)
- **Mini Wallbox Plus** (EIAW-E22KTSE6B15)
- Any OCPP 2.0.1 compatible charger should work

Solar source tested with:
- **Deye / Sunsynk** via Solarman integration
- Any inverter exposing power sensors in W (positive) and grid in W (negative = export)

---

## Installation

### Via HACS (recommended)
1. HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/your-repo/bmw-wallbox-solar` → Integration
3. Install "BMW Wallbox Solar Dynamic Charging"
4. Restart Home Assistant

### Manual
Copy `custom_components/bmw_wallbox_solar/` to your HA `custom_components/` folder and restart.

---

## Prerequisites

### SSL Certificate (Required for BMW Wallbox)
BMW wallboxes enforce OCPP over WSS with a valid hostname certificate. Self-signed or IP-based certs are rejected.

Recommended setup: **Cloudflare + Let's Encrypt** (free).

```
# Example with certbot
certbot certonly --dns-cloudflare \
  -d local.yourdomain.com \
  --dns-cloudflare-credentials ~/.secrets/cloudflare.ini
```

Place certs at `/ssl/fullchain.pem` and `/ssl/privkey.pem` in your HA config directory.

### Python dependencies
Automatically installed by HA:
```
ocpp==1.0.1
websockets>=11.0
```

---

## Configuration

1. **Settings → Devices & Services → Add Integration → BMW Wallbox Solar**
2. Fill in OCPP connection details:
   - **Port**: `9000` (default)
   - **SSL Certificate/Key**: paths to your cert files
   - **Charge Point ID**: from your wallbox OCPP settings (e.g. `DE*BMW*E1234567890123456`)
   - **RFID Token**: optional authorization token
   - **Max Current**: 6–32A
3. Point your wallbox OCPP URL to:
   ```
   wss://local.yourdomain.com:9000
   ```

### Solar Entity Configuration (Options)
After setup, go to **Configure** on the integration card to link inverter entities:

| Option | Example entity | Description |
|---|---|---|
| Solar PV Power | `sensor.deye_solar_power` | Total PV generation (W) |
| Grid Power | `sensor.deye_grid_power` | Positive = import, negative = export |
| House Load | `sensor.deye_load_power` | Home consumption excluding charger (W) |
| Battery SOC | `sensor.deye_battery_soc` | State of charge (%) |
| Battery Power | `sensor.deye_battery_power` | Positive = charging, negative = discharging (W) |
| Battery Reserve SOC | `20` | Don't assist EV charging from battery below this % |
| Max Grid Import for EV | `0` | Watts of grid allowed for EV top-up (0 = solar only in that mode) |

---

## Entities

### Sensors
| Entity | Unit | Notes |
|---|---|---|
| `sensor.bmw_wallbox_solar_charging_power` | W | Real-time charger draw |
| `sensor.bmw_wallbox_solar_energy_total` | kWh | Lifetime energy — Energy Dashboard |
| `sensor.bmw_wallbox_solar_energy_session` | Wh | Current session |
| `sensor.bmw_wallbox_solar_current` | A | Total import current |
| `sensor.bmw_wallbox_solar_current_offered` | A | Current limit offered to EV |
| `sensor.bmw_wallbox_solar_voltage` | V | Average voltage |
| `sensor.bmw_wallbox_solar_connector_status` | — | OCPP connector state |
| `sensor.bmw_wallbox_solar_session_duration` | s | Session time |
| `sensor.bmw_wallbox_solar_solar_power_available` | W | PV production |
| `sensor.bmw_wallbox_solar_solar_surplus` | W | Available for EV |
| `sensor.bmw_wallbox_solar_dynamic_current_target` | A | Computed optimal charge amps |
| `sensor.bmw_wallbox_solar_dynamic_charging_mode` | — | Active mode |
| `sensor.bmw_wallbox_solar_charging_source` | — | `solar` / `grid` / `mixed` / `none` |
| Per-phase V/A, power factor, frequency, temperature | — | Disabled by default |

### Binary Sensors
| Entity | Description |
|---|---|
| `binary_sensor.bmw_wallbox_solar_charging` | ON when actively charging |
| `binary_sensor.bmw_wallbox_solar_wallbox_connected` | ON when OCPP session active |
| `binary_sensor.bmw_wallbox_solar_solar_power_sufficient` | ON when surplus ≥ min charge threshold |
| `binary_sensor.bmw_wallbox_solar_grid_exporting` | ON when exporting to grid |

### Controls
| Entity | Description |
|---|---|
| `select.bmw_wallbox_solar_charging_mode` | Fast / Solar Only / Solar + Grid / Off |
| `switch.bmw_wallbox_solar_dynamic_charging` | Enable/disable auto current adjustment |
| `number.bmw_wallbox_solar_current_limit` | Manual current limit slider (0–32A) |
| `number.bmw_wallbox_solar_minimum_charge_current` | Min amps before pausing in solar mode (6–16A) |
| `number.bmw_wallbox_solar_battery_reserve_soc` | Battery floor for EV assist (0–100%) |
| `button.bmw_wallbox_solar_start_charging` | Remote start |
| `button.bmw_wallbox_solar_stop_charging` | Remote stop |
| `button.bmw_wallbox_solar_recalculate_solar_charging` | Force immediate recalculation |

---

## Charging Modes

### Fast (Max Power)
Charges at `max_current` regardless of solar. Uses grid freely.

### Solar Only
Only charges when solar surplus exceeds the minimum current threshold.
If surplus drops below minimum, charging pauses (current set to 0).

### Solar + Grid
Charges at surplus power. Allows up to `grid_export_limit` watts of grid import to supplement.
Respects `battery_reserve_soc` — won't drain battery for EV if SOC is below reserve.

### Off
Stops charging and disables dynamic control.

---

## Example Automations

### Auto-start when sun is strong
```yaml
automation:
  - alias: "Start EV charging when solar surplus is sufficient"
    trigger:
      - platform: state
        entity_id: binary_sensor.bmw_wallbox_solar_solar_power_sufficient
        to: "on"
        for: "00:05:00"
    condition:
      - condition: state
        entity_id: binary_sensor.bmw_wallbox_solar_charging
        state: "off"
    action:
      - service: button.press
        target:
          entity_id: button.bmw_wallbox_solar_start_charging
```

### Switch to Solar+Grid during off-peak tariff
```yaml
automation:
  - alias: "Switch to Solar+Grid during cheap electricity"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.bmw_wallbox_solar_charging_mode
        data:
          option: "Solar + Grid"
```

### Notify when charging source changes
```yaml
automation:
  - alias: "Notify charging source change"
    trigger:
      - platform: state
        entity_id: sensor.bmw_wallbox_solar_charging_source
    action:
      - service: notify.mobile_app
        data:
          message: "EV charging source: {{ states('sensor.bmw_wallbox_solar_charging_source') }}"
```

---

## Architecture

```
BMW Wallbox (OCPP 2.0.1 over WSS)
        │
        ▼
┌─────────────────────────────┐
│  OCPPServer (server.py)     │  WebSocket server on port 9000
│  BMWWallboxChargePoint      │  Handles all OCPP messages
│  ChargerState               │  Live meter values & status
└────────────┬────────────────┘
             │  state updates
             ▼
┌─────────────────────────────┐       ┌──────────────────────────┐
│  SolarController            │◄──────│  Solarman / Deye sensors │
│  (solar_controller.py)      │       │  sensor.deye_solar_power │
│  Reads solar entities       │       │  sensor.deye_grid_power  │
│  Calculates target amps     │       │  sensor.deye_battery_soc │
│  Pushes SetChargingProfile  │       └──────────────────────────┘
└────────────┬────────────────┘
             │  HA entities
             ▼
┌─────────────────────────────┐
│  Sensors / Binary Sensors   │
│  Numbers / Select / Switch  │
│  Buttons                    │
└─────────────────────────────┘
```

---

## Deye / Solarman Entity Mapping

If you use the [Solarman](https://github.com/StephanJoubert/home_assistant_solarman) integration with a Deye inverter, map entities like this:

| Integration option | Solarman/Deye entity |
|---|---|
| Solar PV Power | `sensor.deye_solar_power` or `sensor.deye_daily_production` |
| Grid Power | `sensor.deye_grid_power` (neg = export) |
| House Load | `sensor.deye_load_power` |
| Battery SOC | `sensor.deye_battery_soc` |
| Battery Power | `sensor.deye_battery_power` |

---

## Troubleshooting

**Wallbox won't connect**
- Check OCPP URL format: `wss://hostname:9000` (not IP, not `ws://`)
- Verify SSL cert hostname matches exactly
- Confirm Charge Point ID in both HA and wallbox settings match

**Dynamic current not changing**
- Check that the solar entities are populated and not `unavailable`
- Press "Recalculate Solar Charging" button to force an update
- Ensure "Dynamic Charging" switch is ON
- Check HA logs for `bmw_wallbox_solar` entries

**Energy dashboard not showing data**
- Add `sensor.bmw_wallbox_solar_energy_total` as an "Individual device" in the Energy Dashboard

---

## License

MIT — see LICENSE file.

## Acknowledgements

Inspired by:
- [JoaoPedroBelo/bmw-wallbox-ha](https://github.com/JoaoPedroBelo/bmw-wallbox-ha) — OCPP 2.0.1 BMW wallbox HA integration
- [AndreasFridh/bmw_wallboxproxy](https://github.com/AndreasFridh/bmw_wallboxproxy) — BMW wallbox proxy research
- [StephanJoubert/home_assistant_solarman](https://github.com/StephanJoubert/home_assistant_solarman) — Solarman/Deye entity structure
- [mobilityhouse/ocpp](https://github.com/mobilityhouse/ocpp) — Python OCPP library
