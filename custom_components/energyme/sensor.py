"""Platform for sensor integration."""

from datetime import timedelta
from http import HTTPStatus
import logging

import requests
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigType
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DECIMALS = 1
SAMPLE_INTERVAL = timedelta(seconds=10)
TOTAL_CHANNELS = 17
TIMEOUT = 5

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_URL): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    url = config.get(CONF_URL)
    data = EnergyMeData(url)

    channel_data = get_channel(url)

    sensors = []
    sensors.append(EnergyMeSensor(data, 0, None, "voltage", "V"))
    for i in range(0, TOTAL_CHANNELS):  # 17 channels
        sensors.append(
            EnergyMeSensor(data, i, channel_data[str(i)]["label"], "activePower", "W")
        )
        sensors.append(
            EnergyMeSensor(data, i, channel_data[str(i)]["label"], "activeEnergy", "Wh")
        )

    add_entities(sensors)


def get_channel(url: str) -> list:
    """Get the channel data from the API."""

    channel_data = [f"Channel {i}" for i in range(0, TOTAL_CHANNELS)]

    try:
        response = requests.get(f"http://{url}/rest/get-channel", timeout=TIMEOUT)
    except requests.exceptions.RequestException as exception:
        _LOGGER.error(exception)
        return channel_data

    if response.status_code == HTTPStatus.OK:
        channel_data = response.json()
    else:
        _LOGGER.warning(
            (
                "Please verify if the specified configuration value "
                "'%s' is correct! (HTTP Status_code = %d)"
            ),
            url,
            response.status_code,
        )

    return channel_data


class EnergyMeData:
    """The class for handling the data retrieval."""

    def __init__(self, url) -> None:
        """Initialize the data object."""
        self._url = url
        self._interval = SAMPLE_INTERVAL
        self.data = None

    @Throttle(SAMPLE_INTERVAL)
    def update(self):
        """Get the latest data from the API."""
        try:
            response = requests.get(f"http://{self._url}/rest/meter", timeout=TIMEOUT)
        except requests.exceptions.RequestException as exception:
            _LOGGER.error(exception)
            return

        if response.status_code == HTTPStatus.OK:
            self.data = response.json()
        else:
            _LOGGER.error(
                (
                    "Please verify if the specified configuration value "
                    "'%s' is correct! (HTTP Status_code = %d)"
                ),
                self._url,
                response.status_code,
            )


class EnergyMeSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(
        self, data: EnergyMeData, index, label, sensor_type, unit_of_measurement
    ) -> None:
        """Initialize the sensor."""
        self._state = None
        self._data = data
        self._sensor_type = sensor_type
        self._index = index
        self._icon = "mdi:flash"
        self._attr_device_class = None
        self._attr_state_class = None
        self._unit_of_measurement = unit_of_measurement

        self._name = "EnergyMe"
        self._name += f" - {label}" if label else ""
        self._name += f" - {self.parse_sensor_type(sensor_type)}"

        if unit_of_measurement == "Wh":
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL
        elif unit_of_measurement == "W":
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif unit_of_measurement == "V":
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self) -> str:
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._data.update()

        data = self._data.data

        for item in data:
            if self._sensor_type in item["data"] and int(item["index"]) == self._index:
                self._state = round(float(item["data"][self._sensor_type]), DECIMALS)

    def parse_sensor_type(self, sensor_type: str) -> str:
        """Parse the sensor type."""
        if sensor_type == "activePower":
            return "Active Power"
        elif sensor_type == "activeEnergy":
            return "Active Energy"
        elif sensor_type == "voltage":
            return "Voltage"
        else:
            return sensor_type
