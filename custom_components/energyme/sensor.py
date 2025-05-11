"""Platform for sensor integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,  # Add this import
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.const import (
    UnitOfEnergy, # For Wh/kWh
    UnitOfPower, # For W/kW
    UnitOfElectricCurrent, # For A
    UnitOfElectricPotential, # For V
    POWER_VOLT_AMPERE_REACTIVE, # For var
    UnitOfApparentPower, # For VA
)


from .const import DOMAIN, CONF_HOST

_LOGGER = logging.getLogger(__name__)

# Define a structure for your sensor types
# (API Key, Friendly Name Suffix, Unit, Device Class, State Class, Icon (optional))
SENSOR_TYPES_MAPPING = {
    "voltage": ("Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "mdi:sine-wave"),
    "current": ("Current", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "mdi:current-ac"),
    "activePower": ("Active Power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "mdi:flash"),
    "reactivePower": ("Reactive Power", POWER_VOLT_AMPERE_REACTIVE, SensorDeviceClass.REACTIVE_POWER, SensorStateClass.MEASUREMENT, "mdi:flash-outline"),
    "apparentPower": ("Apparent Power", UnitOfApparentPower.VOLT_AMPERE, SensorDeviceClass.APPARENT_POWER, SensorStateClass.MEASUREMENT, "mdi:flash-triangle"),
    "powerFactor": ("Power Factor", None, SensorDeviceClass.POWER_FACTOR, SensorStateClass.MEASUREMENT, "mdi:angle-acute"), # Unit is dimensionless
    "activeEnergyImported": ("Active Energy Imported", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "mdi:chart-histogram"),
    "activeEnergyExported": ("Active Energy Exported", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "mdi:chart-histogram-outline"), # Different icon for export
    "reactiveEnergyImported": ("Reactive Energy Imported", "varh", None, SensorStateClass.TOTAL_INCREASING, "mdi:chart-scatter-plot"), # No specific device class, varh
    "reactiveEnergyExported": ("Reactive Energy Exported", "varh", None, SensorStateClass.TOTAL_INCREASING, "mdi:chart-scatter-plot-hexbin"), # No specific device class, varh
    "apparentEnergy": ("Apparent Energy", "VAh", None, SensorStateClass.TOTAL_INCREASING, "mdi:chart-areaspline"), # No specific device class, VAh
}
DECIMALS = 2 # Adjusted for potentially finer values like power factor

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Wait for the coordinator to have data
    if not coordinator.last_update_success or not coordinator.data:
        # This typically shouldn't happen if async_config_entry_first_refresh was awaited
        _LOGGER.warning("Coordinator has no data, deferring sensor setup")
        # You might raise ConfigEntryNotReady here if it's critical,
        # but sensors will just appear as unavailable until data arrives.
        # return

    channel_configs = coordinator.data.get("channels", {}) # from /rest/get-channel
    # meter_data_list = coordinator.data.get("meter", []) # from /rest/meter

    sensors = []
    
    # The /rest/get-channel provides channel activity and labels
    # The /rest/meter provides the actual data, indexed
    
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
    
    # Let's assume for now that the number of items in meter_data_list is fixed (e.g., 17)
    # and we only light up sensors for those whose index is in active_channel_labels.
    
    # Instead of iterating meter_data_list (which changes), iterate potential channels
    # and active_channel_labels.
    
    max_channels_possible = 17 # As per your original TOTAL_CHANNELS
    
    for channel_index in range(max_channels_possible):
        if channel_index in active_channel_labels:
            channel_label = active_channel_labels[channel_index]
            
            # For each metric in SENSOR_TYPES_MAPPING, create a sensor
            for api_key, (name_suffix, unit, dev_class, state_class, icon) in SENSOR_TYPES_MAPPING.items():
                # Special handling for voltage: API might provide it once or per channel.
                # Your API's /rest/meter shows voltage *inside each channel's data object*.
                # So, create voltage sensor for each active channel.

                sensors.append(
                    EnergyMeSensor(
                        coordinator=coordinator,
                        entry_id=entry.entry_id,
                        channel_index=channel_index,
                        channel_label=channel_label,
                        api_key=api_key,
                        name_suffix=name_suffix,
                        unit=unit,
                        device_class=dev_class,
                        state_class=state_class,
                        icon_override=icon,
                    )
                )

    async_add_entities(sensors)


class EnergyMeSensor(CoordinatorEntity, SensorEntity):
    """Representation of an EnergyMe Sensor."""

    _attr_has_entity_name = True # Use if names are like "Device Friendly Name Sensor Name"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str, # For unique ID generation
        channel_index: int,
        channel_label: str,
        api_key: str,
        name_suffix: str,
        unit: Optional[str],
        device_class: Optional[SensorDeviceClass],
        state_class: Optional[SensorStateClass],
        icon_override: Optional[str] = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._channel_index = channel_index
        self._api_key = api_key # e.g., "activePower"
        
        # Construct a unique ID: domain_entryid_channelX_apikey
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_ch{channel_index}_{api_key}"
        
        # Initialize self.entity_description with key and dynamic name
        # The 'key' should be a stable identifier for this type of sensor description.
        # 'api_key' (e.g., "voltage", "activePower") is a good candidate.
        self.entity_description = SensorEntityDescription(
            key=api_key, 
            name=f"{channel_label} {name_suffix}"
        )

        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if icon_override:
            self._attr_icon = icon_override
        elif unit == UnitOfEnergy.WATT_HOUR: # Default energy icon if not overridden
             self._attr_icon = "mdi:chart-bar"
        elif unit == UnitOfPower.WATT: # Default power icon
             self._attr_icon = "mdi:flash"
        
        # Device Info: Link all sensors to a single device entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)}, # Matches unique_id of config_entry
            "name": f"EnergyMe ({coordinator.hass.data[DOMAIN][entry_id].config_entry.data.get(CONF_HOST)})", # Get host from entry data
            "manufacturer": "EnergyMe Open Source", # Replace if you have this info
            # "model": "ESP32-S3 Energy Meter", # Replace if you have this info
            # "sw_version": coordinator.data.get("firmware_version"), # If available in coordinator data
        }
        # Ensure coordinator.data is not None before accessing
        # Firmware version might be fetched from /rest/device-info and added to coordinator data
        # For now, keeping it simple.

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return None
            
        meter_data_list = self.coordinator.data.get("meter", [])
        
        # Find the data for our specific channel_index
        channel_data = None
        for item in meter_data_list:
            if item.get("index") == self._channel_index:
                channel_data = item.get("data")
                break
        
        if channel_data and self._api_key in channel_data:
            try:
                value = float(channel_data[self._api_key])
                return round(value, DECIMALS)
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