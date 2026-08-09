"""Platform for LED light control."""
import logging

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import (
    AUTHOR,
    COMPANY,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    MIN_LED_FIRMWARE_VERSION,
    MODEL,
)
from .led_api import EnergyMeLedClient, raise_if_unsupported

_LOGGER = logging.getLogger(__name__)

DEFAULT_RGB_COLOR = (255, 255, 255)

SERVICE_LED_FLASH = "led_flash"
SERVICE_LED_RELEASE = "led_release"
ATTR_DURATION_MS = "duration_ms"
MAX_FLASH_DURATION_MS = 60000


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

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_LED_FLASH,
        {
            vol.Required(ATTR_RGB_COLOR): vol.All(
                vol.ExactSequence((cv.byte, cv.byte, cv.byte)), vol.Coerce(tuple)
            ),
            vol.Required(ATTR_DURATION_MS): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=MAX_FLASH_DURATION_MS)
            ),
        },
        "async_led_flash",
    )
    platform.async_register_entity_service(
        SERVICE_LED_RELEASE,
        {},
        "async_led_release",
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
        self._client = EnergyMeLedClient(
            coordinator.hass, self._host, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )

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

    @property
    def extra_state_attributes(self) -> dict | None:
        """Expose which layer is currently rendering.

        A network/alert/critical condition outranks the user layer and
        silently masks whatever color was last set here - without this,
        that looks like the color "didn't take". "layer" being anything
        other than "user" or "status" is why.
        """
        if not self.coordinator.data:
            return None
        return {"layer": self.coordinator.data.get("layer")}

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the LED on, optionally setting its color."""
        self._raise_if_unsupported()
        rgb_color = kwargs.get(ATTR_RGB_COLOR) or self.rgb_color or DEFAULT_RGB_COLOR
        await self._client.async_set_color(rgb_color, pattern="solid")

        if ATTR_BRIGHTNESS in kwargs:
            device_brightness = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)
            await self._client.async_set_brightness(device_brightness)

        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the LED off.

        Sends pattern "off" rather than releasing the layer, so the LED goes
        dark instead of reverting to the device's ambient status color.
        """
        self._raise_if_unsupported()
        await self._client.async_set_color(self.rgb_color or DEFAULT_RGB_COLOR, pattern="off")
        await self.coordinator.async_refresh()

    async def async_led_flash(self, rgb_color: tuple[int, int, int], duration_ms: int) -> None:
        """Hold a color for a fixed duration, then release control automatically.

        Unlike turn_on/turn_off, this releases the user layer once the
        duration elapses instead of leaving the LED pinned to this color -
        the device handles the timer itself, so it fires even if HA is
        offline when it expires.
        """
        self._raise_if_unsupported()
        await self._client.async_set_color(rgb_color, pattern="solid", duration_ms=duration_ms)
        await self.coordinator.async_refresh()

    async def async_led_release(self) -> None:
        """Release the user layer, handing control back to the device.

        Unlike turn_off (which forces the LED dark), this reveals whatever
        the device would otherwise be showing - normally its ambient status
        color, or a network/alert/critical indication if one is active.
        """
        self._raise_if_unsupported()
        await self._client.async_release()
        await self.coordinator.async_refresh()

    def _raise_if_unsupported(self) -> None:
        raise_if_unsupported(
            self.available, self.coordinator.last_update_success, self._host, MIN_LED_FIRMWARE_VERSION
        )
