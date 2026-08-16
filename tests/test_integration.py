"""End-to-end entity and command tests for the Aduro integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, call, patch

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryDisabler
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aduro.const import (
    CONF_NAME,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL,
    DOMAIN,
)
from custom_components.aduro.models import AduroData

TEST_DATA = AduroData(
    status={
        "boiler_temp": 21.5,
        "smoke_temp": 95.0,
        "state": 5.0,
        "substate": 0.0,
        "state_sec": 120.0,
        "power_pct": 42.0,
        "operation_mode": 0.0,
        "regulation.fixed_power": 50.0,
    },
    settings={
        "boiler": {"temp": 23.0},
        "regulation": {"operation_mode": 0.0, "fixed_power": 50.0},
        "auger": {"forced_run": 5.0},
    },
)


async def test_entities_and_all_legacy_commands(hass: HomeAssistant) -> None:
    """All legacy discovery entities and write paths remain available."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Wohnzimmerofen",
        unique_id="001234",
        data={
            CONF_NAME: "Wohnzimmerofen",
            "host": "192.0.2.10",
            CONF_SERIAL: "001234",
            CONF_PIN: "9876000000",
            CONF_SCAN_INTERVAL: 30,
        },
    )
    entry.add_to_hass(hass)

    with (
        patch("custom_components.aduro.api.AduroApi.poll", return_value=TEST_DATA),
        patch("custom_components.aduro.api.AduroApi.set_value") as set_value,
        patch(
            "custom_components.aduro.coordinator.asyncio.sleep",
            new=AsyncMock(),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(registry, entry.entry_id)
        assert len(entries) == 11

        by_unique_id = {item.unique_id: item for item in entries}
        for key in (
            "room_temperature",
            "state_code",
            "substate_code",
            "state_duration",
        ):
            assert by_unique_id[f"001234_{key}"].disabled_by is RegistryEntryDisabler.INTEGRATION

        climate_id = registry.async_get_entity_id("climate", DOMAIN, "001234_climate")
        switch_id = registry.async_get_entity_id("switch", DOMAIN, "001234_heating")
        select_id = registry.async_get_entity_id("select", DOMAIN, "001234_fixed_power")
        number_id = registry.async_get_entity_id("number", DOMAIN, "001234_force_auger")
        smoke_id = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            "001234_smoke_temperature",
        )
        state_id = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            "001234_operating_state",
        )
        power_id = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            "001234_power_percentage",
        )

        assert all(
            (
                climate_id,
                switch_id,
                select_id,
                number_id,
                smoke_id,
                state_id,
                power_id,
            )
        )
        climate_state = hass.states.get(climate_id)
        assert climate_state is not None
        assert climate_state.state == "heat"
        assert climate_state.attributes["current_temperature"] == 21.5
        assert climate_state.attributes["temperature"] == 23.0
        assert hass.states.get(switch_id).state == "on"
        assert hass.states.get(select_id).state == "50"
        assert hass.states.get(number_id).state == "5.0"
        assert hass.states.get(smoke_id).state == "95.0"
        assert hass.states.get(state_id).state == "Betrieb, Normal"
        assert hass.states.get(power_id).state == "42.0"

        await hass.services.async_call(
            "switch",
            "turn_on",
            {ATTR_ENTITY_ID: switch_id},
            blocking=True,
        )
        await hass.services.async_call(
            "switch",
            "turn_off",
            {ATTR_ENTITY_ID: switch_id},
            blocking=True,
        )
        await hass.services.async_call(
            "climate",
            "set_temperature",
            {ATTR_ENTITY_ID: climate_id, "temperature": 22},
            blocking=True,
        )
        await hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {ATTR_ENTITY_ID: climate_id, "hvac_mode": "auto"},
            blocking=True,
        )
        await hass.services.async_call(
            "select",
            "select_option",
            {ATTR_ENTITY_ID: select_id, "option": "50"},
            blocking=True,
        )
        await hass.services.async_call(
            "number",
            "set_value",
            {ATTR_ENTITY_ID: number_id, "value": 15},
            blocking=True,
        )

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert set_value.call_args_list == [
        call("misc.start", "1"),
        call("misc.stop", "1"),
        call("boiler.temp", 22.0),
        call("regulation.operation_mode", 1),
        call("regulation.fixed_power", 50),
        call("auger.forced_run", 15),
    ]
