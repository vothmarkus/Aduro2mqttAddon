"""Sensor platform for the Aduro integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import AduroDataUpdateCoordinator
from .entity import AduroEntity
from .models import AduroData, as_int, state_text


@dataclass(frozen=True, kw_only=True)
class AduroSensorEntityDescription(SensorEntityDescription):
    """Describe an Aduro status sensor."""

    value_fn: Callable[[AduroData], StateType]


SENSORS: tuple[AduroSensorEntityDescription, ...] = (
    AduroSensorEntityDescription(
        key="room_temperature",
        translation_key="room_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.status.get("boiler_temp"),
    ),
    AduroSensorEntityDescription(
        key="smoke_temperature",
        translation_key="smoke_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.status.get("smoke_temp"),
    ),
    AduroSensorEntityDescription(
        key="operating_state",
        translation_key="operating_state",
        icon="mdi:state-machine",
        value_fn=lambda data: state_text(data.status),
    ),
    AduroSensorEntityDescription(
        key="state_code",
        translation_key="state_code",
        entity_registry_enabled_default=False,
        value_fn=lambda data: as_int(data.status.get("state")),
    ),
    AduroSensorEntityDescription(
        key="substate_code",
        translation_key="substate_code",
        entity_registry_enabled_default=False,
        value_fn=lambda data: as_int(data.status.get("substate")),
    ),
    AduroSensorEntityDescription(
        key="state_duration",
        translation_key="state_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: as_int(data.status.get("state_sec")),
    ),
    AduroSensorEntityDescription(
        key="power_percentage",
        translation_key="power_percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.status.get("power_pct"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Aduro sensors."""
    async_add_entities(
        AduroSensor(entry.runtime_data, entry, description) for description in SENSORS
    )


class AduroSensor(AduroEntity, SensorEntity):
    """Represent one value from the stove status payload."""

    entity_description: AduroSensorEntityDescription

    def __init__(
        self,
        coordinator: AduroDataUpdateCoordinator,
        entry: ConfigEntry,
        description: AduroSensorEntityDescription,
    ) -> None:
        self.entity_description = description
        super().__init__(coordinator, entry, description.key)

    @property
    def native_value(self) -> Any:
        """Return the latest sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
