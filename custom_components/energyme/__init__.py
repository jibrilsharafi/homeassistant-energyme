"""The EnergyMe integration."""
import asyncio
import logging
from datetime import timedelta

import voluptuous as vol
import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_HOST, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Define the platforms that this integration will support
PLATFORMS = ["sensor"]


async def async_update_options_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    new_scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    _LOGGER.debug(
        "Updating scan interval for %s to %s seconds",
        entry.title,
        new_scan_interval,
    )
    coordinator.update_interval = timedelta(seconds=new_scan_interval)
    # Optionally, you might want to request a refresh if the interval change should trigger an immediate update
    # await coordinator.async_request_refresh()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EnergyMe from a config entry."""
    host = entry.data[CONF_HOST]
    session = async_get_clientsession(hass)

    # Get scan interval from options, fallback to default
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    # Create an API client or coordinator instance
    async def async_update_data():
        """Fetch data from API endpoint."""
        # Note: Using hass.async_add_executor_job for synchronous requests
        # If your device/API supported asyncio, you'd use session.get directly
        try:
            # Fetch channel configuration (less frequent, could be separate or on setup)
            channel_config_url = f"http://{host}/rest/get-channel"
            raw_channel_config = await hass.async_add_executor_job(
                requests.get, channel_config_url, {"timeout": 5}
            )
            raw_channel_config.raise_for_status()
            channel_config = raw_channel_config.json()

            # Fetch meter data
            meter_data_url = f"http://{host}/rest/meter"
            raw_meter_data = await hass.async_add_executor_job(
                requests.get, meter_data_url, {"timeout": 5}
            )
            raw_meter_data.raise_for_status()
            meter_data = raw_meter_data.json()

            # Combine or structure as needed for sensors
            # For now, just return both; sensors will pick what they need
            return {"channels": channel_config, "meter": meter_data}

        except requests.exceptions.Timeout:
            _LOGGER.error("Timeout connecting to EnergyMe device at %s", host)
            raise UpdateFailed(f"Timeout connecting to EnergyMe device at {host}")
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Error connecting to EnergyMe device at %s", host)
            raise UpdateFailed(f"Error connecting to EnergyMe device at {host}")
        except requests.exceptions.HTTPError as err:
            _LOGGER.error("HTTP error from EnergyMe device: %s", err)
            raise UpdateFailed(f"HTTP error from EnergyMe device: {err}")
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching EnergyMe data")
            raise UpdateFailed(f"Unexpected error: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_coordinator_{host}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),  # Use configured scan_interval
    )

    # Fetch initial data so we have it when entities are set up.
    # If the fetch fails, it will raise ConfigEntryNotReady and setup will retry.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
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