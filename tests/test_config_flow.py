"""Tests for the Aduro config and options flows."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aduro.api import AduroConnectionError
from custom_components.aduro.const import (
    CONF_NAME,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL,
    DOMAIN,
)
from custom_components.aduro.models import AduroData

USER_INPUT = {
    CONF_NAME: "Wohnzimmerofen",
    CONF_HOST: "192.0.2.10",
    CONF_SERIAL: "1234",
    CONF_PIN: "9876",
    CONF_SCAN_INTERVAL: 30,
}


async def test_user_flow_creates_normalized_entry(hass: HomeAssistant) -> None:
    """A reachable stove can be configured entirely through the UI."""
    with (
        patch("custom_components.aduro.api.AduroApi.get_status", return_value={}),
        patch("custom_components.aduro.api.AduroApi.poll", return_value=AduroData()),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        assert result["type"] is data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Wohnzimmerofen"
    assert result["data"] == {
        **USER_INPUT,
        CONF_SERIAL: "001234",
        CONF_PIN: "9876000000",
    }


async def test_user_flow_rejects_unreachable_stove(hass: HomeAssistant) -> None:
    """A timeout is shown as a connection error and preserves the form."""
    with patch(
        "custom_components.aduro.api.AduroApi.get_status",
        side_effect=AduroConnectionError("offline"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=USER_INPUT,
        )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_rejects_duplicate_serial(hass: HomeAssistant) -> None:
    """The normalized controller serial is the unique config-entry ID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="001234",
        data={**USER_INPUT, CONF_SERIAL: "001234", CONF_PIN: "9876000000"},
    )
    entry.add_to_hass(hass)

    with patch("custom_components.aduro.api.AduroApi.get_status", return_value={}):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=USER_INPUT,
        )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_validate_and_normalize_connection(hass: HomeAssistant) -> None:
    """Host, PIN, and interval remain editable without recreating the device."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Wohnzimmerofen",
        unique_id="001234",
        data={
            **USER_INPUT,
            CONF_SERIAL: "001234",
            CONF_PIN: "9876000000",
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.aduro.api.AduroApi.get_status", return_value={}):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is data_entry_flow.FlowResultType.FORM

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.0.2.20",
                CONF_PIN: "123",
                CONF_SCAN_INTERVAL: 45,
            },
        )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_HOST: "192.0.2.20",
        CONF_PIN: "1230000000",
        CONF_SCAN_INTERVAL: 45,
    }
