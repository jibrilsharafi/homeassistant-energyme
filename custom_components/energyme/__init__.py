"""The EnergyMe integration."""

import logging
from datetime import timedelta

import requests
from requests.auth import HTTPDigestAuth
from http import HTTPStatus

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL,
    SYSTEM_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Define the platforms that this integration will support
PLATFORMS = ["sensor"]

TIMEOUT_REQUESTS = 10

async def async_update_options_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    meter_coordinator: DataUpdateCoordinator = coordinators["meter_coordinator"]
    new_scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    _LOGGER.debug(
        "Updating scan interval for %s to %s seconds",
        entry.title,
        new_scan_interval,
    )
    # Only update the meter coordinator interval (system coordinator stays at fixed interval)
    meter_coordinator.update_interval = timedelta(seconds=new_scan_interval)

    # Reload the entry to update sensor selection
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EnergyMe from a config entry."""
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    # Get scan interval from options, fallback to default
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    # Create digest auth object
    auth = HTTPDigestAuth(username, password)

    # Create separate coordinators for meter and system data
    async def async_update_meter_data():
        """Fetch meter data from API endpoint."""
        try:
            # Fetch channel configuration using new API endpoint
            channel_config_url = f"http://{host}/api/v1/ade7953/channel"

            def get_channel_config():
                return requests.get(
                    channel_config_url,
                    auth=auth,
                    timeout=TIMEOUT_REQUESTS,
                    headers={"accept": "application/json"}
                )

            raw_channel_config = await hass.async_add_executor_job(get_channel_config)
            raw_channel_config.raise_for_status()
            channel_config = raw_channel_config.json()

            # Fetch meter data using new API endpoint
            meter_data_url = f"http://{host}/api/v1/ade7953/meter-values"

            def get_meter_data():
                return requests.get(
                    meter_data_url,
                    auth=auth,
                    timeout=TIMEOUT_REQUESTS,
                    headers={"accept": "application/json"}
                )

            raw_meter_data = await hass.async_add_executor_job(get_meter_data)
            raw_meter_data.raise_for_status()
            meter_data = raw_meter_data.json()

            return {"channels": channel_config, "meter": meter_data}

        except requests.exceptions.HTTPError as err:
            if err.response.status_code == HTTPStatus.UNAUTHORIZED.value:
                _LOGGER.error("Authentication failed for EnergyMe device at %s", host)
                raise ConfigEntryAuthFailed(
                    f"Authentication failed for EnergyMe device at {host}"
                ) from err
            _LOGGER.error("HTTP error from EnergyMe device: %s", err)
            raise UpdateFailed(f"HTTP error from EnergyMe device: {err}") from err
        except requests.exceptions.Timeout:
            _LOGGER.error("Timeout connecting to EnergyMe device at %s", host)
            raise UpdateFailed(f"Timeout connecting to EnergyMe device at {host}")
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Error connecting to EnergyMe device at %s", host)
            raise UpdateFailed(f"Error connecting to EnergyMe device at {host}")
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching EnergyMe meter data")
            raise UpdateFailed(f"Unexpected error: {err}")

    async def async_update_system_data():
        """Fetch system data from API endpoint."""
        try:
            # Fetch device info for system sensors
            device_info_url = f"http://{host}/api/v1/system/info"

            def get_device_info():
                return requests.get(
                    device_info_url,
                    auth=auth,
                    timeout=TIMEOUT_REQUESTS,
                    headers={"accept": "application/json"}
                )

            raw_device_info = await hass.async_add_executor_job(get_device_info)
            raw_device_info.raise_for_status()
            device_info = raw_device_info.json()

            # Fetch update info (non-critical, handle errors gracefully)
            update_info = {}
            try:
                update_info_url = f"http://{host}/api/v1/firmware/update-info"

                def get_update_info():
                    return requests.get(
                        update_info_url,
                        auth=auth,
                        timeout=TIMEOUT_REQUESTS,
                        headers={"accept": "application/json"}
                    )

                raw_update_info = await hass.async_add_executor_job(get_update_info)
                raw_update_info.raise_for_status()
                update_info = raw_update_info.json()
            except Exception as err:
                _LOGGER.warning(
                    "Failed to fetch update info from EnergyMe device at %s: %s. "
                    "Update sensors will be unavailable.",
                    host,
                    err
                )

            # Combine the data
            return {"device_info": device_info, "update_info": update_info}

        except requests.exceptions.HTTPError as err:
            if err.response.status_code == HTTPStatus.UNAUTHORIZED.value:
                _LOGGER.error("Authentication failed for EnergyMe device at %s for system data", host)
                raise ConfigEntryAuthFailed(
                    f"Authentication failed for EnergyMe device at {host}"
                ) from err
            _LOGGER.error("HTTP error from EnergyMe device for system data: %s", err)
            raise UpdateFailed(f"HTTP error from EnergyMe device: {err}") from err
        except requests.exceptions.Timeout:
            _LOGGER.error("Timeout connecting to EnergyMe device at %s for system data", host)
            raise UpdateFailed(f"Timeout connecting to EnergyMe device at {host}")
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Error connecting to EnergyMe device at %s for system data", host)
            raise UpdateFailed(f"Error connecting to EnergyMe device at {host}")
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching EnergyMe system data")
            raise UpdateFailed(f"Unexpected error: {err}")

    # Create meter data coordinator (configurable interval)
    meter_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_meter_coordinator_{host}",
        update_method=async_update_meter_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    # Create system data coordinator (fixed interval)
    system_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_system_coordinator_{host}",
        update_method=async_update_system_data,
        update_interval=timedelta(seconds=SYSTEM_SCAN_INTERVAL),  # Fixed interval
    )

    # Fetch initial data so we have it when entities are set up.
    # If the fetch fails, it will raise ConfigEntryNotReady and setup will retry.
    await meter_coordinator.async_config_entry_first_refresh()
    await system_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "meter_coordinator": meter_coordinator,
        "system_coordinator": system_coordinator,
        "config_entry": entry,
    }

    # Forward the setup to the sensor platform.
    # Using new method for HA 2022.11+
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Add listener for options flow updates
    entry.async_on_unload(entry.add_update_listener(async_update_options_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok