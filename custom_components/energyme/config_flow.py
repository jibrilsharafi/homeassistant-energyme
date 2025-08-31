"""Config flow for EnergyMe."""
import logging

import requests
from requests.auth import HTTPDigestAuth
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_NAME  # If you want to allow naming the device

from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL  # Added auth constants

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
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
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                # Test connection - use /api/v1/health with digest auth
                # We need to run this in an executor since requests is blocking
                health_url = f"http://{host}/api/v1/health"

                # Using hass.async_add_executor_job for synchronous requests with digest auth
                def make_request():
                    return requests.get(
                        health_url,
                        auth=HTTPDigestAuth(username, password),
                        timeout=5,
                        headers={"accept": "application/json"}
                    )

                response = await self.hass.async_add_executor_job(make_request)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

                # Check response content for the health endpoint
                health_data = response.json()
                if health_data.get("status") != "ok":
                    _LOGGER.warning("Health check returned non-ok status: %s", health_data.get("status"))

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
                    errors["base"] = "cannot_connect_http"  # Generic HTTP error
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return EnergyMeOptionsFlowHandler(config_entry)


class EnergyMeOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle EnergyMe options."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize EnergyMe options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current_scan_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),  # Ensure positive integer, min 1 second
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
