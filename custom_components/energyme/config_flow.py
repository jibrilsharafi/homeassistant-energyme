"""Config flow for EnergyMe."""
import logging
from typing import Any

import requests
from requests.auth import HTTPDigestAuth
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_NAME
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class EnergyMeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EnergyMe."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_device_id: str | None = None
        self._discovered_model: str | None = None
        self._discovered_version: str | None = None
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def _test_connection(
        self, host: str, username: str, password: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Test connection to device and return system info.

        Returns:
            Tuple of (system_info dict, None) on success, or (None, error_key) on failure.

        """
        try:
            info_url = f"http://{host}/api/v1/system/info"

            def make_request():
                return requests.get(
                    info_url,
                    auth=HTTPDigestAuth(username, password),
                    timeout=5,
                    headers={"accept": "application/json"}
                )

            response = await self.hass.async_add_executor_job(make_request)
            response.raise_for_status()
            return response.json(), None

        except requests.exceptions.Timeout:
            _LOGGER.error("Timeout connecting to %s", host)
            return None, "cannot_connect_timeout"
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Failed to connect to %s", host)
            return None, "cannot_connect"
        except requests.exceptions.HTTPError as err:
            _LOGGER.error("HTTP error connecting to %s: %s", host, err)
            if err.response.status_code == 401:
                return None, "invalid_auth"
            return None, "cannot_connect_http"
        except Exception as e:
            _LOGGER.exception("Unexpected exception: %s", e)
            return None, "unknown"

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if not entry:
            return self.async_abort(reason="reconfigure_failed")

        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # Test connection with new credentials
            system_info, error = await self._test_connection(host, username, password)

            if error:
                errors["base"] = error
            else:
                # Only verify device ID if both the new connection returns one AND we have one stored
                # This allows reconfiguration even if device_id is not available
                new_device_id = system_info.get("static", {}).get("device", {}).get("id", "")
                old_device_id = entry.unique_id

                # Skip device_id check if either is missing or if unique_id was the host (legacy setup)
                should_verify_id = new_device_id and old_device_id and old_device_id != entry.data.get(CONF_HOST, "")

                if should_verify_id and new_device_id != old_device_id:
                    errors["base"] = "device_mismatch"
                    _LOGGER.error(
                        "Device ID mismatch: expected %s, got %s",
                        old_device_id,
                        new_device_id
                    )
                else:
                    _LOGGER.info(
                        "Reconfigure successful for device at %s (device_id: %s, verified: %s)",
                        host,
                        new_device_id or "not available",
                        should_verify_id
                    )
                    # Update the config entry with new connection details
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_HOST: host,
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                        }
                    )

                    # Reload the entry to apply changes
                    await self.hass.config_entries.async_reload(entry.entry_id)

                    return self.async_abort(reason="reconfigure_successful")

        # Pre-fill with current values
        current_host = entry.data.get(CONF_HOST, "")
        current_username = entry.data.get(CONF_USERNAME, "")

        reconfigure_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_host): str,
                vol.Required(CONF_USERNAME, default=current_username): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=reconfigure_schema,
            errors=errors,
            description_placeholders={
                "device_id": entry.unique_id or "unknown",
            }
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle reauthorization request."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reauthorization confirmation."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # Use the existing host from the config entry
            host = self._reauth_entry.data[CONF_HOST]

            # Test connection with new credentials
            system_info, error = await self._test_connection(host, username, password)

            if error:
                errors["base"] = error
            else:
                # Only verify device ID if both the new connection returns one AND we have one stored
                new_device_id = system_info.get("static", {}).get("device", {}).get("id", "")
                old_device_id = self._reauth_entry.unique_id

                # Skip device_id check if either is missing (could be legacy setup or device doesn't provide it)
                should_verify_id = new_device_id and old_device_id and old_device_id != host

                if should_verify_id and new_device_id != old_device_id:
                    errors["base"] = "device_mismatch"
                    _LOGGER.error(
                        "Device ID mismatch during reauth: expected %s, got %s",
                        old_device_id,
                        new_device_id
                    )
                else:
                    _LOGGER.info(
                        "Reauth successful for device at %s (device_id: %s, verified: %s)",
                        host,
                        new_device_id or "not available",
                        should_verify_id
                    )
                    # Update credentials
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry,
                        data={
                            **self._reauth_entry.data,
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                        }
                    )

                    await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

        current_username = self._reauth_entry.data.get(CONF_USERNAME, "")

        reauth_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=current_username): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=reauth_schema,
            errors=errors,
            description_placeholders={
                "host": self._reauth_entry.data.get(CONF_HOST, ""),
            }
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle zeroconf discovery."""
        _LOGGER.debug("Zeroconf discovery: %s", discovery_info)

        # Extract information from discovery
        host = str(discovery_info.host)
        properties = discovery_info.properties

        # Get device_id from properties for unique identification
        device_id = properties.get("device_id", "")
        model = properties.get("model", "Home")
        version = properties.get("version", "")
        vendor = properties.get("vendor", "")

        # Verify this is an EnergyMe device
        if vendor.lower() != "energyme":
            return self.async_abort(reason="not_energyme_device")

        # Store discovered information for later steps
        self._discovered_host = host
        self._discovered_device_id = device_id
        self._discovered_model = model
        self._discovered_version = version

        # Check if already configured by device_id
        if device_id:
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        # Also check for legacy entries that used host as unique_id
        for entry in self._async_current_entries():
            if entry.data.get(CONF_HOST) == host:
                return self.async_abort(reason="already_configured")

        # If no device_id available, fall back to host
        if not device_id:
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

        # Set the title for the discovery notification
        self.context["title_placeholders"] = {
            "name": f"EnergyMe {model}",
            "host": host,
        }

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle user confirmation of discovered device."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            host = self._discovered_host

            # Test connection with provided credentials
            _, error = await self._test_connection(host, username, password)

            if error:
                errors["base"] = error
            else:
                # Create config entry with discovered host
                data = {
                    CONF_HOST: host,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                }

                title = f"EnergyMe {self._discovered_model} @ {host}"
                return self.async_create_entry(title=title, data=data)

        # Schema for zeroconf confirmation - only need credentials
        zeroconf_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=zeroconf_schema,
            errors=errors,
            description_placeholders={
                "host": self._discovered_host,
                "model": self._discovered_model,
                "version": self._discovered_version,
            },
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # Test connection with provided credentials
            system_info, error = await self._test_connection(host, username, password)

            if error:
                errors["base"] = error
            else:
                # Get device_id from system info for unique identification
                device_id = system_info.get("static", {}).get("device", {}).get("id", "")

                # Set a unique ID for the config entry to prevent duplicates
                # Use device_id if available, otherwise fall back to host
                unique_id = device_id if device_id else host
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, f"EnergyMe @ {host}"), data=user_input
                )

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
        # self.config_entry is now set automatically by the parent class

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

            # Create the final options data with only scan interval
            options_data = {
                CONF_SCAN_INTERVAL: scan_interval,
            }

            return self.async_create_entry(title="", data=options_data)

        current_scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        options_schema = vol.Schema({
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=current_scan_interval,
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            description_placeholders={
                "scan_interval_help": "Set the polling interval in seconds for meter data (voltage, power, energy, etc.)."
            }
        )
