"""Constants for BMW Wallbox Solar Dynamic Charging integration."""

DOMAIN = "bmw_wallbox_solar"

# Config entry keys
CONF_PORT = "port"
CONF_SSL_CERT = "ssl_cert"
CONF_SSL_KEY = "ssl_key"
CONF_CHARGE_POINT_ID = "charge_point_id"
CONF_RFID_TOKEN = "rfid_token"
CONF_MAX_CURRENT = "max_current"

# Solar / dynamic charging config
CONF_SOLAR_POWER_ENTITY = "solar_power_entity"
CONF_GRID_POWER_ENTITY = "grid_power_entity"
CONF_HOUSE_LOAD_ENTITY = "house_load_entity"
CONF_BATTERY_SOC_ENTITY = "battery_soc_entity"
CONF_BATTERY_POWER_ENTITY = "battery_power_entity"
CONF_DYNAMIC_CHARGING_ENABLED = "dynamic_charging_enabled"
CONF_SOLAR_PRIORITY = "solar_priority"
CONF_MIN_CHARGE_CURRENT = "min_charge_current"
CONF_GRID_EXPORT_LIMIT = "grid_export_limit"
CONF_BATTERY_RESERVE_SOC = "battery_reserve_soc"

# Defaults
DEFAULT_PORT = 9000
DEFAULT_MAX_CURRENT = 32
DEFAULT_MIN_CURRENT = 6
DEFAULT_BATTERY_RESERVE_SOC = 20
DEFAULT_GRID_EXPORT_LIMIT = 0  # W, 0 = no limit on export
DEFAULT_UPDATE_INTERVAL = 30  # seconds

# SSL modes
SSL_MODE_NONE = "none"        # plain ws:// — use a reverse proxy for TLS
SSL_MODE_AUTO = "auto"        # reuse HA's built-in Let's Encrypt cert
SSL_MODE_MANUAL = "manual"    # explicit cert + key paths

SSL_MODES = [SSL_MODE_NONE, SSL_MODE_AUTO, SSL_MODE_MANUAL]

CONF_SSL_MODE = "ssl_mode"

# OCPP
OCPP_SUBPROTOCOL = "ocpp2.0.1"

# Data keys stored in hass.data[DOMAIN][entry_id]
DATA_CHARGER = "charger"
DATA_SERVER = "server"
DATA_SOLAR_CONTROLLER = "solar_controller"

# Sensor / entity unique ID suffixes
SENSOR_POWER = "power"
SENSOR_ENERGY_TOTAL = "energy_total"
SENSOR_ENERGY_SESSION = "energy_session"
SENSOR_CURRENT_IMPORT = "current_import"
SENSOR_CURRENT_OFFERED = "current_offered"
SENSOR_VOLTAGE = "voltage"
SENSOR_CURRENT_L1 = "current_l1"
SENSOR_CURRENT_L2 = "current_l2"
SENSOR_CURRENT_L3 = "current_l3"
SENSOR_VOLTAGE_L1 = "voltage_l1"
SENSOR_VOLTAGE_L2 = "voltage_l2"
SENSOR_VOLTAGE_L3 = "voltage_l3"
SENSOR_POWER_ACTIVE_IMPORT = "power_active_import"
SENSOR_POWER_REACTIVE_IMPORT = "power_reactive_import"
SENSOR_POWER_FACTOR = "power_factor"
SENSOR_FREQUENCY = "frequency"
SENSOR_TEMPERATURE = "temperature"
SENSOR_CHARGING_STATE = "charging_state"
SENSOR_CONNECTOR_STATUS = "connector_status"
SENSOR_TRANSACTION_ID = "transaction_id"
SENSOR_SESSION_DURATION = "session_duration"
SENSOR_SESSION_ENERGY_COST = "session_energy_cost"

# Solar dynamic sensors
SENSOR_SOLAR_POWER = "solar_power_available"
SENSOR_GRID_POWER = "grid_power"
SENSOR_DYNAMIC_CURRENT_TARGET = "dynamic_current_target"
SENSOR_DYNAMIC_MODE = "dynamic_mode"
SENSOR_SOLAR_SURPLUS = "solar_surplus"
SENSOR_CHARGING_SOURCE = "charging_source"

# Number entity keys
NUMBER_CURRENT_LIMIT = "current_limit"
NUMBER_MIN_CHARGE_CURRENT = "min_charge_current"
NUMBER_BATTERY_RESERVE_SOC = "battery_reserve_soc"

# Select entity keys
SELECT_CHARGING_MODE = "charging_mode"

# Switch entity keys
SWITCH_DYNAMIC_CHARGING = "dynamic_charging"

# Binary sensor keys
BINARY_SENSOR_CHARGING = "charging"
BINARY_SENSOR_CONNECTED = "connected"
BINARY_SENSOR_SOLAR_SUFFICIENT = "solar_sufficient"
BINARY_SENSOR_GRID_EXPORT = "grid_exporting"

# Charging modes
CHARGING_MODE_FAST = "fast"
CHARGING_MODE_SOLAR_ONLY = "solar_only"
CHARGING_MODE_SOLAR_GRID = "solar_grid"
CHARGING_MODE_SCHEDULED = "scheduled"
CHARGING_MODE_OFF = "off"

CHARGING_MODES = [
    CHARGING_MODE_FAST,
    CHARGING_MODE_SOLAR_ONLY,
    CHARGING_MODE_SOLAR_GRID,
    CHARGING_MODE_OFF,
]

# OCPP Connector States
CONNECTOR_AVAILABLE = "Available"
CONNECTOR_OCCUPIED = "Occupied"
CONNECTOR_UNAVAILABLE = "Unavailable"
CONNECTOR_FAULTED = "Faulted"
CONNECTOR_CHARGING = "Charging"
CONNECTOR_FINISHING = "Finishing"
CONNECTOR_SUSPENDED_EV = "SuspendedEV"
CONNECTOR_SUSPENDED_EVSE = "SuspendedEVSE"
