"""Constants for the EnergyMe integration."""

DOMAIN = "energyme"
CONF_HOST = "host" # Replaces CONF_URL, more standard for IP/hostname
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
DEFAULT_SCAN_INTERVAL = 10 # Seconds - for meter data
CONF_SCAN_INTERVAL = "scan_interval" # Added for options flow
SYSTEM_SCAN_INTERVAL = 60 # Seconds - fixed interval for system sensors (temperature, wifi, memory)

# Sensor selection configuration
CONF_SENSORS = "sensors"
DEFAULT_SENSORS = [
    "voltage",
    "activePower",
    "powerFactor",
    "activeEnergyImported"
]

# System sensors are always created regardless of sensor selection
# These update every 60 seconds on a separate coordinator
SYSTEM_SENSORS = [
    "firmware_version",
    "device_id",
    "temperature",
    "wifi_rssi",
    "heap_free_percentage",
]
