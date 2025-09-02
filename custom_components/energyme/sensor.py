"""Platform for sensor integration."""
import logging
import dataclasses

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,  # Add this import
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.const import (
    UnitOfEnergy, # For Wh/kWh
    UnitOfPower, # For W/kW
    UnitOfElectricCurrent, # For A
    UnitOfElectricPotential, # For V
    UnitOfReactivePower, # For var
    UnitOfApparentPower, # For VA
)


from .const import DOMAIN, CONF_HOST, CONF_SENSORS, DEFAULT_SENSORS, SYSTEM_SENSORS

_LOGGER = logging.getLogger(__name__)

# TODO: add auto discovery via mDNS
# TODO: test first default credentials (and in any case only ask for the password, the username is always the same)
# TODO: split the sensors in meter sensors and system sensors
# TODO: sensors should be disabled by default except necessary ones
# TODO: clean comments and docs

# Define a structure for your sensor types
# (API Key, Friendly Name Suffix, Unit, Device Class, State Class, Icon (optional))
SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "voltage": SensorEntityDescription(
        key="voltage",
        name="Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
    ),
    "current": SensorEntityDescription(
        key="current",
        name="Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:current-ac",
    ),
    "activePower": SensorEntityDescription(
        key="activePower",
        name="Active Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash",
    ),
    "reactivePower": SensorEntityDescription(
        key="reactivePower",
        name="Reactive Power",
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash-outline",
    ),
    "apparentPower": SensorEntityDescription(
        key="apparentPower",
        name="Apparent Power",
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash-triangle",
    ),
    "powerFactor": SensorEntityDescription(
        key="powerFactor",
        name="Power Factor",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:angle-acute",
    ),
    "activeEnergyImported": SensorEntityDescription(
        key="activeEnergyImported",
        name="Active Energy Imported",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:chart-histogram",
    ),
    "activeEnergyExported": SensorEntityDescription(
        key="activeEnergyExported",
        name="Active Energy Exported",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:chart-histogram-outline",
    ),
    "reactiveEnergyImported": SensorEntityDescription(
        key="reactiveEnergyImported",
        name="Reactive Energy Imported",
        native_unit_of_measurement="varh",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:chart-scatter-plot",
    ),
    "reactiveEnergyExported": SensorEntityDescription(
        key="reactiveEnergyExported",
        name="Reactive Energy Exported",
        native_unit_of_measurement="varh",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:chart-scatter-plot-hexbin",
    ),
    "apparentEnergy": SensorEntityDescription(
        key="apparentEnergy",
        name="Apparent Energy",
        native_unit_of_measurement="VAh",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:chart-areaspline",
    ),
}

# System information sensors (not per-channel)
SYSTEM_SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "firmware_version": SensorEntityDescription(
        key="firmware_version",
        name="Firmware Version",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=None,
        icon="mdi:chip",
    ),
    "device_id": SensorEntityDescription(
        key="device_id",
        name="Device ID",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=None,
        icon="mdi:identifier",
    ),
    "temperature": SensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
    ),
    "wifi_rssi": SensorEntityDescription(
        key="wifi_rssi",
        name="WiFi Signal Strength",
        native_unit_of_measurement="dBm",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wifi-strength-2",
    ),
    "heap_free_percentage": SensorEntityDescription(
        key="heap_free_percentage",
        name="Heap Memory Free",
        native_unit_of_measurement="%",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:memory",
    ),
}

# Per-metric rounding
DECIMALS_MAP: dict[str, int] = {
    "voltage": 1,
    "current": 3,
    "activePower": 1,
    "reactivePower": 1,
    "apparentPower": 1,
    "powerFactor": 3,
    "activeEnergyImported": 0,
    "activeEnergyExported": 0,
    "reactiveEnergyImported": 0,
    "reactiveEnergyExported": 0,
    "apparentEnergy": 0,
}
DEFAULT_DECIMALS = 2

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Get enabled sensors from options, fallback to defaults
    enabled_sensors = entry.options.get(CONF_SENSORS, DEFAULT_SENSORS)

    # Wait for the coordinator to have data
    if not coordinator.last_update_success or not coordinator.data:
        # This typically shouldn't happen if async_config_entry_first_refresh was awaited
        _LOGGER.warning("Coordinator has no data, deferring sensor setup")
        # You might raise ConfigEntryNotReady here if it's critical,
        # but sensors will just appear as unavailable until data arrives.
        # return

    channel_configs = coordinator.data.get("channels", {}) # from /api/v1/ade7953/channel
    # Handle the response structure from the API
    if isinstance(channel_configs, dict) and "channels" in channel_configs:
        # API returns {"channels": [...]}
        channel_configs = channel_configs["channels"]

    # Normalize channel_configs to a dict keyed by index-string so downstream code can rely on .items()
    if isinstance(channel_configs, list):
        _LOGGER.debug("channel_configs is a list, normalizing to dict")
        normalized = {}
        for i, item in enumerate(channel_configs):
            # item may itself be a dict with an 'index' field
            key = str(item.get("index", i)) if isinstance(item, dict) else str(i)
            normalized[key] = item
        channel_configs = normalized

    sensors = []

    # Add system sensors (not channel-specific) - always enabled
    for api_key, description in SYSTEM_SENSOR_DESCRIPTIONS.items():
        if api_key in SYSTEM_SENSORS:  # Only create defined system sensors
            sensors.append(
                EnergyMeSystemSensor(
                    coordinator=coordinator,
                    entry_id=entry.entry_id,
                    api_key=api_key,
                    entity_description=description,
                )
            )

    # The /api/v1/ade7953/channel endpoint provides channel activity and labels
    # The /api/v1/ade7953/meter-values endpoint provides the actual data

    # Create a map of index to channel label from channel_configs for active channels
    active_channel_labels = {}
    for ch_index_str, ch_data in channel_configs.items():
        if ch_data.get("active", False):
            active_channel_labels[int(ch_index_str)] = ch_data.get("label", f"Channel {ch_index_str}")

    # Iterate through meter data, which is an array.
    # Each item in meter_data_list corresponds to a channel.
    # We only create sensors for channels marked active in channel_configs.

    # The coordinator fetches all meter data. Sensors will pull from this.
    # We need to know the structure of meter_data_list to create sensors.
    # Assuming meter_data_list is like:
    # [ {"index": 0, "label": "Main", "data": {"voltage": 230, ...}}, ... ]

    # EnergyMe device supports up to 17 channels
    # Only create sensors for active channels

    # Instead of iterating meter_data_list (which changes), iterate potential channels
    # and active_channel_labels.

    max_channels_possible = 17  # EnergyMe device maximum channel count

    for channel_index in range(max_channels_possible):
        if channel_index in active_channel_labels:
            channel_label = active_channel_labels[channel_index]

            # For each enabled metric in SENSOR_DESCRIPTIONS, create a sensor
            for api_key, description in SENSOR_DESCRIPTIONS.items():
                if api_key in enabled_sensors:  # Only create sensors for enabled ones
                    # Create sensor using central SensorEntityDescription
                    sensors.append(
                        EnergyMeSensor(
                            coordinator=coordinator,
                            entry_id=entry.entry_id,
                            channel_index=channel_index,
                            channel_label=channel_label,
                            api_key=api_key,
                            entity_description=description,
                        )
                    )

    async_add_entities(sensors)


class EnergyMeSensor(CoordinatorEntity, SensorEntity):
    """Representation of an EnergyMe Sensor."""

    _attr_has_entity_name = True # Use if names are like "Device Friendly Name Sensor Name"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str,  # For unique ID generation
        channel_index: int,
        channel_label: str,
        api_key: str,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._channel_index = channel_index
        self._api_key = api_key # e.g., "activePower"

        # Construct a unique ID: domain_entryid_channelX_apikey
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_ch{channel_index}_{api_key}"

        # Create a copy of the provided SensorEntityDescription with a channel-specific name.
        # SensorEntityDescription is a frozen dataclass, so use dataclasses.replace.
        self.entity_description = dataclasses.replace(
            entity_description,
            name=f"{channel_label} {entity_description.name}",
            key=api_key,
        )

        # Apply common attributes from the description
        self._attr_native_unit_of_measurement = entity_description.native_unit_of_measurement
        self._attr_device_class = entity_description.device_class
        self._attr_state_class = entity_description.state_class
        if entity_description.icon:
            self._attr_icon = entity_description.icon
        else:
            unit = entity_description.native_unit_of_measurement
            if unit == UnitOfEnergy.WATT_HOUR:  # Default energy icon if not provided
                self._attr_icon = "mdi:chart-bar"
            elif unit == UnitOfPower.WATT:  # Default power icon
                self._attr_icon = "mdi:flash"

        # Device Info: Link all sensors to a single device entry
        device_data = coordinator.data.get("device_info", {}) if coordinator.data else {}
        # Extract device ID and firmware version from system info structure
        static_info = device_data.get("static", {})
        device_id = static_info.get("device", {}).get("id") or entry_id
        firmware_version = static_info.get("firmware", {}).get("buildVersion")

        # Get host from config entry for a cleaner device name
        host = coordinator.hass.data[DOMAIN][entry_id].config_entry.data.get(CONF_HOST)
        device_name = f"EnergyMe {host.split('.')[-1] if '.' in host else host}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)}, # Use actual device ID if available
            "name": device_name,
            "manufacturer": "Jibril Sharafi",
            "model": "EnergyMe - Home",
        }

        # Add firmware version if available
        if firmware_version:
            self._attr_device_info["sw_version"] = firmware_version

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return None

        meter_data_list = self.coordinator.data.get("meter", [])
        # Normalize meter_data_list: accept dict (keyed by index) or list of items
        if isinstance(meter_data_list, dict):
            _LOGGER.debug("meter data is a dict, normalizing to list")
            normalized = []
            for k, v in meter_data_list.items():
                try:
                    idx = int(k)
                except Exception:
                    idx = None
                # If v already has 'data', keep structure; else wrap
                if isinstance(v, dict) and "data" in v:
                    normalized.append({"index": idx if idx is not None else 0, "data": v.get("data")})
                else:
                    normalized.append({"index": idx if idx is not None else 0, "data": v})
            meter_data_list = normalized

        # Find the data for our specific channel_index
        channel_data = None
        for item in meter_data_list:
            if item.get("index") == self._channel_index:
                channel_data = item.get("data")
                break

        if channel_data and self._api_key in channel_data:
            try:
                value = float(channel_data[self._api_key])
                decimals = DECIMALS_MAP.get(self._api_key, DEFAULT_DECIMALS)
                return round(value, decimals)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid value for %s on channel %s: %s",
                    self._api_key,
                    self._channel_index,
                    channel_data[self._api_key]
                )
                return None
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Available if the coordinator is successful and the specific data point exists
        if not self.coordinator.last_update_success:
            return False

        # Check if the specific data point is available (it might not be for some reason)
        # This is implicitly handled by native_value returning None if data isn't there.
        # A more explicit check could be added if needed.
        return super().available

    # The name property is now handled by self.entity_description.name and _attr_has_entity_name = True
    # The icon, unit_of_measurement, device_class, state_class are set as _attr_ properties.


class EnergyMeSystemSensor(CoordinatorEntity, SensorEntity):
    """Representation of an EnergyMe System Sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str,
        api_key: str,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the system sensor."""
        super().__init__(coordinator)
        self._api_key = api_key

        # Construct a unique ID: domain_entryid_system_apikey
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_system_{api_key}"

        # Use the provided entity description
        self.entity_description = entity_description

        # Device Info: Link system sensor to the same device as channel sensors
        if coordinator.data:
            device_data = coordinator.data.get("device_info", {})
            static_info = device_data.get("static", {})
            device_id = static_info.get("device", {}).get("id") or entry_id
            firmware_version = static_info.get("firmware", {}).get("buildVersion")

            # Get host from config entry for device name
            host = coordinator.hass.data[DOMAIN][entry_id].config_entry.data.get(CONF_HOST)
            device_name = f"EnergyMe {host.split('.')[-1] if '.' in host else host}"

            self._attr_device_info = {
                "identifiers": {(DOMAIN, device_id)},
                "name": device_name,
                "manufacturer": "Jibril Sharafi",
                "model": "EnergyMe - Home",
            }

            # Add firmware version if available
            if firmware_version:
                self._attr_device_info["sw_version"] = firmware_version

    @property
    def native_value(self):
        """Return the state of the sensor based on system info."""
        if not self.coordinator.data:
            return None

        device_info = self.coordinator.data.get("device_info", {})
        if not device_info:
            return None

        # Extract values based on the API key
        if self._api_key == "firmware_version":
            return device_info.get("static", {}).get("firmware", {}).get("buildVersion")
        elif self._api_key == "device_id":
            return device_info.get("static", {}).get("device", {}).get("id")
        elif self._api_key == "temperature":
            temp_value = device_info.get("dynamic", {}).get("performance", {}).get("temperatureCelsius")
            if temp_value is not None:
                try:
                    return round(float(temp_value), 1)
                except (ValueError, TypeError):
                    return temp_value
            return temp_value
        elif self._api_key == "wifi_rssi":
            return device_info.get("dynamic", {}).get("network", {}).get("wifiRssi")
        elif self._api_key == "heap_free_percentage":
            heap_info = device_info.get("dynamic", {}).get("memory", {}).get("heap", {})
            free_percentage = heap_info.get("freePercentage")
            if free_percentage is not None:
                try:
                    return round(float(free_percentage), 1)
                except (ValueError, TypeError):
                    return free_percentage
            return free_percentage

        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None
