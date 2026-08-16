"""Data coordinator for the Aduro integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AduroApi, AduroError
from .const import COMMAND_REFRESH_DELAY, DOMAIN
from .models import AduroData

LOGGER = logging.getLogger(__name__)


class AduroDataUpdateCoordinator(DataUpdateCoordinator[AduroData]):
    """Coordinate serialized polling and commands for an Aduro stove."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: AduroApi,
        update_interval: int,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
            always_update=False,
        )
        self.api = api

    async def _async_update_data(self) -> AduroData:
        try:
            return await self.hass.async_add_executor_job(self.api.poll, self.data)
        except AduroError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_value(self, path: str, value: Any) -> None:
        """Write a value and reproduce the legacy delayed immediate refresh."""
        try:
            await self.hass.async_add_executor_job(self.api.set_value, path, value)
        except AduroError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"path": path},
            ) from err

        await asyncio.sleep(COMMAND_REFRESH_DELAY)
        await self.async_request_refresh()


type AduroConfigEntry = ConfigEntry[AduroDataUpdateCoordinator]
