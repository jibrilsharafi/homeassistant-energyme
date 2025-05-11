"""Config flow for EnergyMe."""
import logging

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_NAME # If you want to allow naming the device

from .const import DOMAIN, CONF_HOST

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        # vol.Optional(CONF_NAME, default="EnergyMe"): str, # Optional: allow user to name it
    }
)


class EnergyMeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EnergyMe."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            try:
                # Test connection - use /rest/is-alive
                # We need to run this in an executor since requests is blocking
                is_alive_url = f"http://{host}/rest/is-alive"
                
                # Using hass.async_add_executor_job for synchronous requests
                response = await self.hass.async_add_executor_job(
                    requests.get, is_alive_url, {"timeout": 5}
                )
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                
                # Check response content if necessary, e.g., response.json().get("message") == "True"
                # For now, a 200 OK is sufficient proof of "alive"
                
                # Set a unique ID for the config entry to prevent duplicates
                # You could use a device MAC address or serial if available from an info endpoint
                # For now, host is unique enough for this purpose.
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, f"EnergyMe @ {host}"), data=user_input
                )

            except requests.exceptions.Timeout:
                _LOGGER.error("Timeout connecting to %s", host)
                errors["base"] = "cannot_connect_timeout"
            except requests.exceptions.ConnectionError:
                _LOGGER.error("Failed to connect to %s", host)
                errors["base"] = "cannot_connect"
            except requests.exceptions.HTTPError as err:
                _LOGGER.error("HTTP error connecting to %s: %s", host, err)
                if err.response.status_code == 401:
                     errors["base"] = "invalid_auth"
                else:
                     errors["base"] = "cannot_connect_http" # Generic HTTP error
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    # If you want to add options flow later (e.g., for update interval)
    # @staticmethod
    # @callback
    # def async_get_options_flow(config_entry):
    #     return EnergyMeOptionsFlowHandler(config_entry)

# class EnergyMeOptionsFlowHandler(config_entries.OptionsFlow):
#    def __init__(self, config_entry: config_entries.ConfigEntry):
#        self.config_entry = config_entry
#
#    async def async_step_init(self, user_input=None):
#        # Manage an options flow for scan interval, etc.
#        pass