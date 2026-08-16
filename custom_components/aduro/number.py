"""Number platform for the Aduro integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AduroDataUpdateCoordinator
from .entity import AduroEntity
from .models import as_float


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Aduro numbers."""
    async_add_entities([AduroForceAugerNumber(entry.runtime_data, entry)])


class AduroForceAugerNumber(AduroEntity, NumberEntity):
    """Force the auger to run for a configured number of seconds."""

    _attr_translation_key = "force_auger"
    _attr_icon = "mdi:screw-lag"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 120
    _attr_native_step = 5
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator: AduroDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "force_auger")

    @property
    def native_value(self) -> float | None:
        """Return the configured forced run time."""
        return as_float(self.coordinator.data.setting("auger", "forced_run", 0))

    async def async_set_native_value(self, value: float) -> None:
        """Set the forced auger run time."""
        await self.coordinator.async_set_value("auger.forced_run", int(value))
