"""Small HTTP client for the EnergyMe device's LED write endpoints."""
import logging

import requests
from requests.auth import HTTPDigestAuth

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

TIMEOUT_REQUESTS = 10


class EnergyMeLedClient:
    """Wraps the device's /api/v1/led/* write endpoints.

    Shared by the light and switch platforms so the request/auth/error
    handling for LED writes lives in one place.
    """

    def __init__(self, hass: HomeAssistant, host: str, username: str, password: str) -> None:
        """Initialize the client."""
        self._hass = hass
        self._host = host
        self._auth = HTTPDigestAuth(username, password)

    async def async_set_color(
        self, rgb_color: tuple[int, int, int], pattern: str, duration_ms: int | None = None
    ) -> None:
        """PUT a color/pattern to the user layer, optionally with an auto-release timer."""
        red, green, blue = rgb_color
        url = f"http://{self._host}/api/v1/led/color"
        payload = {"red": red, "green": green, "blue": blue, "pattern": pattern}
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms

        def put_color():
            return requests.put(
                url,
                auth=self._auth,
                timeout=TIMEOUT_REQUESTS,
                headers={"accept": "application/json"},
                json=payload,
            )

        await self._async_request(put_color, "set LED color")

    async def async_set_brightness(self, brightness: int) -> None:
        """PUT the device-wide LED brightness (0-100)."""
        url = f"http://{self._host}/api/v1/led/brightness"

        def put_brightness():
            return requests.put(
                url,
                auth=self._auth,
                timeout=TIMEOUT_REQUESTS,
                headers={"accept": "application/json"},
                json={"brightness": brightness},
            )

        await self._async_request(put_brightness, "set LED brightness")

    async def async_release(self) -> None:
        """DELETE the user layer, handing control back to the device."""
        url = f"http://{self._host}/api/v1/led/color"

        def delete_color():
            return requests.delete(
                url,
                auth=self._auth,
                timeout=TIMEOUT_REQUESTS,
                headers={"accept": "application/json"},
            )

        await self._async_request(delete_color, "release LED color")

    async def _async_request(self, func, action: str) -> None:
        """Run a blocking request in the executor and raise on failure."""
        try:
            response = await self._hass.async_add_executor_job(func)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to %s on EnergyMe device at %s: %s", action, self._host, err)
            raise HomeAssistantError(f"Failed to {action} on EnergyMe device: {err}") from err
