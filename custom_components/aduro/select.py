"""Select platform for the Aduro integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AduroDataUpdateCoordinator
from .entity import AduroEntity
from .models import as_int

FIXED_POWER_OPTIONS = ["10", "50", "100"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Aduro selects."""
    async_add_entities([AduroFixedPowerSelect(entry.runtime_data, entry)])


class AduroFixedPowerSelect(AduroEntity, SelectEntity):
    """Select the fixed output percentage."""

    _attr_translation_key = "fixed_power"
    _attr_options = FIXED_POWER_OPTIONS

    def __init__(self, coordinator: AduroDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "fixed_power")

    @property
    def current_option(self) -> str | None:
        """Return the configured fixed output percentage."""
        value = self.coordinator.data.setting(
            "regulation",
            "fixed_power",
            self.coordinator.data.status.get("regulation.fixed_power"),
        )
        converted = as_int(value)
        return None if converted is None else str(converted)

    async def async_select_option(self, option: str) -> None:
        """Set the fixed output percentage."""
        await self.coordinator.async_set_value("regulation.fixed_power", int(option))
