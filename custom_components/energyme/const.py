"""Constants for the EnergyMe integration."""

AUTHOR = "Jibril Sharafi"
COMPANY = "EnergyMe"
MODEL = "Home"

DOMAIN = "energyme"
CONF_HOST = "host" # Replaces CONF_URL, more standard for IP/hostname
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
DEFAULT_SCAN_INTERVAL = 10 # Seconds - for meter data
CONF_SCAN_INTERVAL = "scan_interval" # Added for options flow
SYSTEM_SCAN_INTERVAL = 900 # Seconds (15 minutes) - fixed interval for system sensors (not critical data)

# System sensors are always created regardless of sensor selection
# These update on a fixed interval on a separate coordinator
SYSTEM_SENSORS = [
    "firmware_version",
    "device_id",
    "temperature",
    "wifi_rssi",
    "wifi_local_ip",
    "heap_free_percentage",
    "uptime",
    "storage_free",
    "update_available",
]
