"""Shared entity base for the Aduro integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AduroDataUpdateCoordinator


class AduroEntity(CoordinatorEntity[AduroDataUpdateCoordinator]):
    """Base class for all entities belonging to one Aduro stove."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AduroDataUpdateCoordinator,
        entry: ConfigEntry,
        entity_key: str,
    ) -> None:
        super().__init__(coordinator)
        identifier = entry.unique_id or coordinator.api.serial
        self._attr_unique_id = f"{identifier}_{entity_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            name=entry.title,
            manufacturer="Aduro",
            model="H2 / NBE controller",
            serial_number=coordinator.api.serial,
        )
