"""Switch platform for the Aduro integration."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AduroDataUpdateCoordinator
from .entity import AduroEntity
from .models import is_heating


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Aduro heating switch."""
    async_add_entities([AduroHeatingSwitch(entry.runtime_data, entry)])


class AduroHeatingSwitch(AduroEntity, SwitchEntity):
    """Start or stop the stove."""

    _attr_translation_key = "heating"
    _attr_icon = "mdi:radiator"

    def __init__(self, coordinator: AduroDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "heating")

    @property
    def is_on(self) -> bool | None:
        """Return the legacy state-code based switch state."""
        return is_heating(self.coordinator.data.status)

    async def async_turn_on(self, **kwargs: object) -> None:
        """Start heating."""
        await self.coordinator.async_set_value("misc.start", "1")

    async def async_turn_off(self, **kwargs: object) -> None:
        """Stop heating."""
        await self.coordinator.async_set_value("misc.stop", "1")
