"""Climate platform for the Aduro integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AduroDataUpdateCoordinator
from .entity import AduroEntity
from .models import as_float, as_int


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Aduro climate entity."""
    async_add_entities([AduroClimate(entry.runtime_data, entry)])


class AduroClimate(AduroEntity, ClimateEntity):
    """Native equivalent of the legacy MQTT climate entity."""

    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT]
    _attr_min_temp = 5
    _attr_max_temp = 35
    _attr_target_temperature_step = 1
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, coordinator: AduroDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "climate")

    @property
    def current_temperature(self) -> float | None:
        """Return room temperature, with the legacy boiler-temperature fallback."""
        status = self.coordinator.data.status
        return as_float(status.get("room_temp", status.get("boiler_temp")))

    @property
    def target_temperature(self) -> float | None:
        """Return the configured room target temperature."""
        return as_float(self.coordinator.data.setting("boiler", "temp"))

    @property
    def hvac_mode(self) -> HVACMode:
        """Return auto/heat from regulation.operation_mode."""
        value = self.coordinator.data.setting(
            "regulation",
            "operation_mode",
            self.coordinator.data.status.get("operation_mode"),
        )
        return HVACMode.AUTO if as_int(value) == 1 else HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the same action calculation as the MQTT climate template."""
        status = self.coordinator.data.status
        power = as_float(status.get("power_pct"))
        if power is not None:
            return HVACAction.OFF if power == 0 else HVACAction.HEATING

        state = as_int(status.get("state"))
        if state is None:
            return None
        return HVACAction.OFF if state in {13, 14, 20, 28} else HVACAction.HEATING

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the room target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.coordinator.async_set_value("boiler.temp", float(temperature))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set automatic or fixed-power operation."""
        if hvac_mode not in self._attr_hvac_modes:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")
        value = 1 if hvac_mode == HVACMode.AUTO else 0
        await self.coordinator.async_set_value("regulation.operation_mode", value)
