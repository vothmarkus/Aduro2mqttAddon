"""Diagnostics support for the Aduro integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import CONF_PIN, CONF_SERIAL
from .coordinator import AduroConfigEntry

TO_REDACT = {
    CONF_HOST,
    CONF_PIN,
    CONF_SERIAL,
    "city",
    "wifi.router",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: AduroConfigEntry,
) -> dict[str, Any]:
    """Return redacted diagnostics for one stove."""
    coordinator = entry.runtime_data
    return {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval is not None
                else None
            ),
        },
        "data": {
            "status": async_redact_data(coordinator.data.status, TO_REDACT),
            "settings": async_redact_data(coordinator.data.settings, TO_REDACT),
        },
    }
