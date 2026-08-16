"""Native Home Assistant integration for Aduro pellet stoves."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .const import CONF_PIN, CONF_SCAN_INTERVAL, CONF_SERIAL, DEFAULT_SCAN_INTERVAL, PLATFORMS

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aduro from a config entry."""
    from .api import AduroApi
    from .coordinator import AduroDataUpdateCoordinator

    config: dict[str, Any] = {**entry.data, **entry.options}
    api = AduroApi(
        host=config["host"],
        serial=config[CONF_SERIAL],
        pin=config[CONF_PIN],
    )
    coordinator = AduroDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        api=api,
        update_interval=config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Aduro config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Aduro after its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
