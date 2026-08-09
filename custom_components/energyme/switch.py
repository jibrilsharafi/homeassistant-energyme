"""Platform for the LED override switch."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    led_coordinator: DataUpdateCoordinator = coordinators["led_coordinator"]
    system_coordinator: DataUpdateCoordinator = coordinators["system_coordinator"]

    device_data = system_coordinator.data.get("device_info", {}) if system_coordinator.data else {}
    base_device_id = device_data.get("static", {}).get("device", {}).get("id") or entry.entry_id

    async_add_entities(
        [EnergyMeLedOverrideSwitch(led_coordinator, entry, base_device_id)]
    )


class EnergyMeLedOverrideSwitch(CoordinatorEntity, SwitchEntity):  # type: ignore[misc]
    """Whether HA is currently overriding the device's ambient LED status.

    On = the user layer is occupied (light is showing a color, or forced
    dark via turn_off). Off = the device is showing its own status/alert
    indication. Turning this off is the simple, one-tap equivalent of the
    led_release service; turning it on re-asserts the LED's current color
    onto the user layer.
    """

    _attr_has_entity_name = True
    _attr_name = "LED Override"
    _attr_icon = "mdi:led-variant-on"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        main_device_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._host = entry.data[CONF_HOST]
        self._client = EnergyMeLedClient(
            coordinator.hass, self._host, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )

        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_led_override"
        self.entity_id = f"switch.{DOMAIN}_{entry.entry_id.lower()}_led_override"
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
        """Return whether HA currently occupies the user layer."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("layer") == "user"

    @property
    def extra_state_attributes(self) -> dict | None:
        """Expose which layer is currently rendering.

        Turning this on writes the user layer, but a network/alert/critical
        condition still outranks it - "layer" shows what's actually winning
        even when this switch itself reports off.
        """
        if not self.coordinator.data:
            return None
        return {"layer": self.coordinator.data.get("layer")}

    async def async_turn_on(self, **kwargs) -> None:
        """Re-assert the LED's current color onto the user layer."""
        self._raise_if_unsupported()
        color = (self.coordinator.data or {}).get("color") or {}
        rgb_color = (
            color.get("red", DEFAULT_RGB_COLOR[0]),
            color.get("green", DEFAULT_RGB_COLOR[1]),
            color.get("blue", DEFAULT_RGB_COLOR[2]),
        )
        await self._client.async_set_color(rgb_color, pattern="solid")
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Release the user layer, handing control back to the device."""
        self._raise_if_unsupported()
        await self._client.async_release()
        await self.coordinator.async_refresh()

    def _raise_if_unsupported(self) -> None:
        raise_if_unsupported(
            self.available, self.coordinator.last_update_success, self._host, MIN_LED_FIRMWARE_VERSION
        )
