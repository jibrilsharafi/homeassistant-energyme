"""Platform for sensor integration."""
import logging
import dataclasses

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,  # Add this import
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfApparentPower,
    UnitOfEnergy,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers import device_registry as dr


from .const import AUTHOR, COMPANY, DOMAIN, CONF_HOST, CONF_SENSORS, DEFAULT_SENSORS, MODEL, SYSTEM_SENSORS

_LOGGER = logging.getLogger(__name__)

# TODO: clean comments and docs
# TODO: add control for LED (can we add only brigthness or also fun RGB?)
# TODO: Add the IP address to the system info
# TODO: ensure that if the IP changes, the device is still recognized as the same device (use device ID from system info)

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
        native_unit_of_measurement="VArh",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:chart-histogram-outline",
    ),
    "reactiveEnergyExported": SensorEntityDescription(
        key="reactiveEnergyExported",
        name="Reactive Energy Exported",
        native_unit_of_measurement="VArh",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:chart-histogram-outline",
    ),
    "apparentEnergy": SensorEntityDescription(
        key="apparentEnergy",
        name="Apparent Energy",
        native_unit_of_measurement="VAh",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:chart-histogram-outline",
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
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "device_id": SensorEntityDescription(
        key="device_id",
        name="Device ID",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=None,
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "temperature": SensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "wifi_rssi": SensorEntityDescription(
        key="wifi_rssi",
        name="WiFi Signal Strength",
        native_unit_of_measurement="dBm",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wifi-strength-2",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "heap_free_percentage": SensorEntityDescription(
        key="heap_free_percentage",
        name="Heap Memory Free",
        native_unit_of_measurement="%",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:memory",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "uptime": SensorEntityDescription(
        key="uptime",
        name="Uptime",
        native_unit_of_measurement="d",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "storage_free": SensorEntityDescription(
        key="storage_free",
        name="Storage Space Available",
        native_unit_of_measurement="%",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:harddisk",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "update_available": SensorEntityDescription(
        key="update_available",
        name="Firmware Update Available",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=None,
        icon="mdi:cloud-download-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
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
    coordinators = hass.data[DOMAIN][entry.entry_id]
    meter_coordinator: DataUpdateCoordinator = coordinators["meter_coordinator"]
    system_coordinator: DataUpdateCoordinator = coordinators["system_coordinator"]

    # Get enabled sensors from options, fallback to defaults
    enabled_sensors = entry.options.get(CONF_SENSORS, DEFAULT_SENSORS)

    # Wait for the coordinators to have data
    if not meter_coordinator.last_update_success or not meter_coordinator.data:
        _LOGGER.warning("Meter coordinator has no data, deferring sensor setup")

    if not system_coordinator.last_update_success or not system_coordinator.data:
        _LOGGER.warning("System coordinator has no data, deferring sensor setup")

    channel_configs = meter_coordinator.data.get("channels", {}) if meter_coordinator.data else {}
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

    # Create the main parent device in the device registry
    device_registry = dr.async_get(hass)

    # Get device info from system coordinator for main device
    device_data = system_coordinator.data.get("device_info", {}) if system_coordinator.data else {}
    static_info = device_data.get("static", {})
    base_device_id = static_info.get("device", {}).get("id") or entry.entry_id
    firmware_version = static_info.get("firmware", {}).get("buildVersion")

    # Get host from config entry for fallback
    config_entry = coordinators["config_entry"]
    host = config_entry.data.get(CONF_HOST)

    # Use device ID if available, otherwise fall back to friendly name or host
    device_name_suffix = base_device_id if base_device_id != entry.entry_id else host.split('.')[-1] if '.' in host else host
    main_device_name = f"{COMPANY} - {MODEL} | {device_name_suffix}"

    # Create the main parent device
    # Note: async_get_or_create() automatically registers the device in HA's device registry
    # as a side effect. The return value (main_device) contains the device object, but the
    # actual registration happens when this function is called. We don't need to use the
    # return value further - the device is now available in the registry.
    main_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, base_device_id)},
        name=main_device_name,
        manufacturer=AUTHOR,
        model=f"{COMPANY} - {MODEL}",
        sw_version=firmware_version,
    )

    # Log that main device was created
    _LOGGER.debug("Created main device: %s with ID: %s", main_device.name, main_device.id)

    # Add system sensors to the main device (not channel-specific) - always enabled
    for api_key, description in SYSTEM_SENSOR_DESCRIPTIONS.items():
        if api_key in SYSTEM_SENSORS:  # Only create defined system sensors
            sensors.append(
                EnergyMeSystemSensor(
                    coordinator=system_coordinator,  # Use system coordinator
                    entry_id=entry.entry_id,
                    api_key=api_key,
                    entity_description=description,
                    main_device_id=base_device_id,  # Pass main device ID
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

    # Create sensors for each active channel
    # Each channel gets its own device that links to the main device via "via_device"
    # This creates a device hierarchy: Main Device -> Channel Devices -> Sensors
    max_channels_possible = 17  # EnergyMe device maximum channel count

    for channel_index in range(max_channels_possible):
        if channel_index in active_channel_labels:
            channel_label = active_channel_labels[channel_index]

            # For each enabled metric in SENSOR_DESCRIPTIONS, create a sensor
            for api_key, description in SENSOR_DESCRIPTIONS.items():
                if api_key in enabled_sensors:  # Only create sensors for enabled ones
                    # Create sensor using central SensorEntityDescription
                    # Each sensor's device_info will create a separate channel device
                    # that automatically links to the main device via "via_device"
                    sensors.append(
                        EnergyMeSensor(
                            coordinator=meter_coordinator,  # Use meter coordinator
                            entry_id=entry.entry_id,
                            channel_index=channel_index,
                            channel_label=channel_label,
                            api_key=api_key,
                            entity_description=description,
                        )
                    )

    async_add_entities(sensors)


class EnergyMeSensor(CoordinatorEntity, SensorEntity):  # type: ignore[misc]
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
        self._base_sensor_name = entity_description.name  # Store base name for dynamic updates

        # Construct a stable unique ID: domain_entryid_channelX_apikey
        # This never changes even if user renames channels or changes device settings
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_ch{channel_index}_{api_key}"

        # Set entity_id explicitly based on unique_id for maximum stability
        # Format: sensor.energyme_{entry_id}_ch{channel_index}_{api_key}
        # This survives channel label changes, ensuring history is preserved
        self.entity_id = f"sensor.{DOMAIN}_{entry_id}_ch{channel_index}_{api_key.lower()}"

        # Set initial friendly name with channel label
        # Format: "{channel_label} - {sensor_name}" (e.g., "General - Active Power")
        # This will be updated dynamically when channel label changes
        self._attr_name = f"{channel_label} - {self._base_sensor_name}"

        # Create entity description without the channel label in name
        # The name will be managed via _attr_name for dynamic updates
        self.entity_description = dataclasses.replace(
            entity_description,
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

        # Device Info: Create separate device for each channel
        # This creates the device hierarchy: Main Device -> Channel Devices -> Sensors
        # The "via_device" parameter automatically links this channel device to the main device

        # Get device info from system coordinator
        coordinators = coordinator.hass.data[DOMAIN][entry_id]
        system_coordinator = coordinators["system_coordinator"]
        device_data = system_coordinator.data.get("device_info", {}) if system_coordinator.data else {}

        # Extract device ID and firmware version from system info structure
        static_info = device_data.get("static", {})
        base_device_id = static_info.get("device", {}).get("id") or entry_id
        firmware_version = static_info.get("firmware", {}).get("buildVersion")

        # Create unique device identifier for this channel using entry_id for stability
        # Using entry_id ensures device identity remains stable even if hardware changes
        channel_device_id = f"{entry_id}_ch{channel_index}"

        # Simple device name: "Channel {index} - {label}"
        # This makes device names clean and focused on the channel itself
        device_name = f"Channel {channel_index} - {channel_label}"

        # The device_info with "via_device" creates the parent-child relationship
        # HomeAssistant automatically handles the device creation and linking
        self._attr_device_info = {
            "identifiers": {(DOMAIN, channel_device_id)},
            "name": device_name,
            "manufacturer": AUTHOR,
            "model": f"{COMPANY} - {MODEL}",
            "via_device": (DOMAIN, base_device_id),  # This links to the main device created above
        }

        # Add firmware version if available
        if firmware_version:
            self._attr_device_info["sw_version"] = firmware_version

    def _update_native_value(self) -> None:
        """Update the native value from coordinator data."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            self._attr_native_value = None
            self._attr_available = False
            return

        # Update channel label if it changed on the device
        channel_configs = self.coordinator.data.get("channels", {})
        if isinstance(channel_configs, dict) and "channels" in channel_configs:
            channel_configs = channel_configs["channels"]

        # Normalize to dict if needed
        if isinstance(channel_configs, list):
            normalized = {}
            for item in channel_configs:
                idx = item.get("index") if isinstance(item, dict) else None
                if idx is not None:
                    normalized[str(idx)] = item
            channel_configs = normalized

        # Get current channel label from device
        channel_data_config = channel_configs.get(str(self._channel_index), {})
        if isinstance(channel_data_config, dict):
            current_label = channel_data_config.get("label", f"Channel {self._channel_index}")

            # Update friendly name if label changed
            new_name = f"{current_label} - {self._base_sensor_name}"
            if self._attr_name != new_name:
                self._attr_name = new_name
                _LOGGER.debug(
                    "Updated friendly name for ch%d %s to: %s",
                    self._channel_index,
                    self._api_key,
                    new_name
                )

            # Update device name if label changed
            new_device_name = f"Channel {self._channel_index} - {current_label}"
            if self._attr_device_info and self._attr_device_info.get("name") != new_device_name:
                self._attr_device_info["name"] = new_device_name

                # Also update in device registry
                identifiers = self._attr_device_info.get("identifiers")
                if identifiers:
                    device_registry = dr.async_get(self.hass)
                    device = device_registry.async_get_device(identifiers=identifiers)
                    if device:
                        device_registry.async_update_device(
                            device.id,
                            name=new_device_name
                        )
                        _LOGGER.debug(
                            "Updated device name for ch%d to: %s",
                            self._channel_index,
                            new_device_name
                        )

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
                self._attr_native_value = round(value, decimals)
                self._attr_available = True
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid value for %s on channel %s: %s",
                    self._api_key,
                    self._channel_index,
                    channel_data[self._api_key]
                )
                self._attr_native_value = None
                self._attr_available = False
        else:
            self._attr_native_value = None
            self._attr_available = True  # Available but no data yet

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_native_value()
        super()._handle_coordinator_update()

    # The name property is now handled by self.entity_description.name and _attr_has_entity_name = True
    # The icon, unit_of_measurement, device_class, state_class are set as _attr_ properties.


class EnergyMeSystemSensor(CoordinatorEntity, SensorEntity):  # type: ignore[misc]
    """Representation of an EnergyMe System Sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str,
        api_key: str,
        entity_description: SensorEntityDescription,
        main_device_id: str,
    ) -> None:
        """Initialize the system sensor."""
        super().__init__(coordinator)
        self._api_key = api_key
        self._main_device_id = main_device_id

        # Construct a stable unique ID: domain_entryid_system_apikey
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_system_{api_key}"

        # Set entity_id explicitly based on unique_id for maximum stability
        # Format: sensor.energyme_{entry_id}_system_{api_key}
        self.entity_id = f"sensor.{DOMAIN}_{entry_id}_system_{api_key.lower()}"

        # Use the provided entity description
        # Entity name will be the friendly name (e.g., "Firmware Version", "Temperature")
        self.entity_description = entity_description

        # Device Info: Link system sensor to the main device
        # System sensors (temperature, WiFi, memory, etc.) belong directly to the main device
        # They use the same identifiers as the main device to attach to it
        if coordinator.data:
            device_data = coordinator.data.get("device_info", {})
            static_info = device_data.get("static", {})
            firmware_version = static_info.get("firmware", {}).get("buildVersion")

            # Get host from config entry for device name
            coordinators = coordinator.hass.data[DOMAIN][entry_id]
            config_entry = coordinators["config_entry"]
            host = config_entry.data.get(CONF_HOST)

            # Use device ID if available, otherwise fall back to friendly name or host
            device_name_suffix = self._main_device_id if self._main_device_id != entry_id else host.split('.')[-1] if '.' in host else host
            device_name = f"{COMPANY} - {MODEL} | {device_name_suffix} - System"

            # Using the same identifiers as the main device links these sensors to it
            self._attr_device_info = {
                "identifiers": {(DOMAIN, self._main_device_id)},
                "name": device_name,
                "manufacturer": AUTHOR,
                "model": f"{COMPANY} - {MODEL}",
            }

            # Add firmware version if available
            if firmware_version:
                self._attr_device_info["sw_version"] = firmware_version

        # Initialize native value from already-fetched coordinator data
        self._update_native_value()

    def _update_native_value(self) -> None:
        """Update the native value from coordinator data."""
        if not self.coordinator.data:
            self._attr_native_value = None
            self._attr_available = False
            return

        device_info = self.coordinator.data.get("device_info", {})
        if not device_info:
            self._attr_native_value = None
            self._attr_available = False
            return

        # Extract values based on the API key
        value = None
        if self._api_key == "firmware_version":
            value = device_info.get("static", {}).get("firmware", {}).get("buildVersion")
        elif self._api_key == "device_id":
            value = device_info.get("static", {}).get("device", {}).get("id")
        elif self._api_key == "temperature":
            temp_value = device_info.get("dynamic", {}).get("performance", {}).get("temperatureCelsius")
            if temp_value is not None:
                try:
                    # Round down to nearest 0.5°C (floor function) to have less data points in HA
                    import math
                    value = math.floor(float(temp_value) * 2) / 2
                except (ValueError, TypeError):
                    value = temp_value
        elif self._api_key == "wifi_rssi":
            value = device_info.get("dynamic", {}).get("network", {}).get("wifiRssi")
        elif self._api_key == "heap_free_percentage":
            heap_info = device_info.get("dynamic", {}).get("memory", {}).get("heap", {})
            free_percentage = heap_info.get("freePercentage")
            if free_percentage is not None:
                try:
                    import math
                    # Round down to nearest 0.5%
                    value = math.floor(float(free_percentage) * 2) / 2
                except (ValueError, TypeError):
                    value = free_percentage
        elif self._api_key == "uptime":
            uptime_seconds = device_info.get("dynamic", {}).get("time", {}).get("uptimeSeconds")
            if uptime_seconds is not None:
                try:
                    # Convert seconds to days, round to 1 decimal place
                    value = round(float(uptime_seconds) / 86400, 1)
                except (ValueError, TypeError):
                    value = uptime_seconds
        elif self._api_key == "storage_free":
            littlefs_info = device_info.get("dynamic", {}).get("storage", {}).get("littlefs", {})
            free_percentage = littlefs_info.get("freePercentage")
            if free_percentage is not None:
                try:
                    # Round down to nearest 0.5%
                    import math
                    value = math.floor(float(free_percentage) * 2) / 2
                except (ValueError, TypeError):
                    value = free_percentage
        elif self._api_key == "update_available":
            # Check if firmware update is available
            # update_info is at the top level of coordinator data
            update_info = self.coordinator.data.get("update_info", {}) if self.coordinator.data else {}
            is_latest = update_info.get("isLatest", True)
            value = "No" if is_latest else "Yes"

        self._attr_native_value = value
        self._attr_available = self.coordinator.last_update_success and value is not None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_native_value()
        super()._handle_coordinator_update()
