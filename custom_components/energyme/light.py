"""Platform for LED light control."""
import logging

import requests
from requests.auth import HTTPDigestAuth

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import AUTHOR, COMPANY, CONF_HOST, CONF_PASSWORD, CONF_USERNAME, DOMAIN, MODEL

_LOGGER = logging.getLogger(__name__)

TIMEOUT_REQUESTS = 10
DEFAULT_RGB_COLOR = (255, 255, 255)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    led_coordinator: DataUpdateCoordinator = coordinators["led_coordinator"]
    system_coordinator: DataUpdateCoordinator = coordinators["system_coordinator"]

    device_data = system_coordinator.data.get("device_info", {}) if system_coordinator.data else {}
    base_device_id = device_data.get("static", {}).get("device", {}).get("id") or entry.entry_id

    async_add_entities(
        [EnergyMeLed(led_coordinator, entry, base_device_id)]
    )


class EnergyMeLed(CoordinatorEntity, LightEntity):  # type: ignore[misc]
    """Representation of the EnergyMe device's status LED."""

    _attr_has_entity_name = True
    _attr_name = "LED"
    _attr_icon = "mdi:led-strip-variant"
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        main_device_id: str,
    ) -> None:
        """Initialize the LED entity."""
        super().__init__(coordinator)
        self._host = entry.data[CONF_HOST]
        self._auth = HTTPDigestAuth(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_led"
        self.entity_id = f"light.{DOMAIN}_{entry.entry_id.lower()}_led"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, main_device_id)},
            "manufacturer": AUTHOR,
            "model": f"{COMPANY} - {MODEL}",
        }

    @property
    def available(self) -> bool:
        """Return whether the LED state is known."""
        return self.coordinator.last_update_success and bool(self.coordinator.data)

    @property
    def is_on(self) -> bool | None:
        """Return whether the LED is currently lit."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("pattern") != "off"

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the RGB color of the LED."""
        if not self.coordinator.data:
            return None
        color = self.coordinator.data.get("color") or {}
        return (
            color.get("red", DEFAULT_RGB_COLOR[0]),
            color.get("green", DEFAULT_RGB_COLOR[1]),
            color.get("blue", DEFAULT_RGB_COLOR[2]),
        )

    @property
    def brightness(self) -> int | None:
        """Return the LED brightness, scaled from the device's 0-100 range to 0-255."""
        if not self.coordinator.data:
            return None
        return round(self.coordinator.data.get("brightness", 0) * 255 / 100)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the LED on, optionally setting its color."""
        rgb_color = kwargs.get(ATTR_RGB_COLOR) or self.rgb_color or DEFAULT_RGB_COLOR
        await self._async_set_color(rgb_color, pattern="solid")

        if ATTR_BRIGHTNESS in kwargs:
            await self._async_set_brightness(kwargs[ATTR_BRIGHTNESS])

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the LED off.

        Sends pattern "off" rather than releasing the layer, so the LED goes
        dark instead of reverting to the device's ambient status color.
        """
        await self._async_set_color(self.rgb_color or DEFAULT_RGB_COLOR, pattern="off")
        await self.coordinator.async_request_refresh()

    async def _async_set_color(self, rgb_color: tuple[int, int, int], pattern: str) -> None:
        """Call the device's LED color endpoint."""
        red, green, blue = rgb_color
        url = f"http://{self._host}/api/v1/led/color"

        def put_color():
            return requests.put(
                url,
                auth=self._auth,
                timeout=TIMEOUT_REQUESTS,
                headers={"accept": "application/json"},
                json={"red": red, "green": green, "blue": blue, "pattern": pattern},
            )

        await self._async_request(put_color, "set LED color")

    async def _async_set_brightness(self, brightness: int) -> None:
        """Call the device's LED brightness endpoint."""
        url = f"http://{self._host}/api/v1/led/brightness"
        device_brightness = round(brightness * 100 / 255)

        def put_brightness():
            return requests.put(
                url,
                auth=self._auth,
                timeout=TIMEOUT_REQUESTS,
                headers={"accept": "application/json"},
                json={"brightness": device_brightness},
            )

        await self._async_request(put_brightness, "set LED brightness")

    async def _async_request(self, func, action: str) -> None:
        """Run a blocking request in the executor and raise on failure."""
        try:
            response = await self.hass.async_add_executor_job(func)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to %s on EnergyMe device at %s: %s", action, self._host, err)
            raise HomeAssistantError(f"Failed to {action} on EnergyMe device: {err}") from err
