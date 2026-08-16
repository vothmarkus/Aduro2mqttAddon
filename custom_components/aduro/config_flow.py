"""Config flow for the Aduro integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .api import (
    AduroApi,
    AduroConnectionError,
    AduroError,
    AduroResponseError,
    normalize_pin,
    normalize_serial,
)
from .const import (
    CONF_NAME,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

LOGGER = logging.getLogger(__name__)


def _required_text(value: Any) -> str:
    """Normalize and validate a required text field."""
    result = str(value).strip()
    if not result:
        raise vol.Invalid("value must not be empty")
    return result


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    values = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=values.get(CONF_NAME, DEFAULT_NAME)): _required_text,
            vol.Required(CONF_HOST, default=values.get(CONF_HOST, "")): _required_text,
            vol.Required(CONF_SERIAL, default=values.get(CONF_SERIAL, "")): _required_text,
            vol.Required(CONF_PIN, default=values.get(CONF_PIN, "")): _required_text,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=values.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            ),
        }
    )


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults[CONF_HOST]): _required_text,
            vol.Required(CONF_PIN, default=defaults[CONF_PIN]): _required_text,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            ),
        }
    )


async def _async_validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize connection data."""
    normalized = dict(data)
    normalized[CONF_HOST] = str(data[CONF_HOST]).strip()
    normalized[CONF_SERIAL] = normalize_serial(data[CONF_SERIAL])
    normalized[CONF_PIN] = normalize_pin(data[CONF_PIN])

    api = AduroApi(
        host=normalized[CONF_HOST],
        serial=normalized[CONF_SERIAL],
        pin=normalized[CONF_PIN],
    )
    await hass.async_add_executor_job(api.get_status)
    return normalized


class AduroConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Aduro config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Configure one stove."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                data = await _async_validate_input(self.hass, user_input)
            except AduroConnectionError:
                errors["base"] = "cannot_connect"
            except AduroResponseError:
                errors["base"] = "invalid_auth"
            except AduroError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - config flows must not leak library errors
                LOGGER.exception("Unexpected error while validating Aduro connection")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(data[CONF_SERIAL])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return AduroOptionsFlow()


class AduroOptionsFlow(config_entries.OptionsFlow):
    """Allow connection and polling settings to be changed."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage Aduro options."""
        current = {**self.config_entry.data, **self.config_entry.options}
        errors: dict[str, str] = {}

        if user_input is not None:
            candidate = {
                **user_input,
                CONF_SERIAL: self.config_entry.data[CONF_SERIAL],
                CONF_NAME: self.config_entry.data.get(CONF_NAME, self.config_entry.title),
            }
            try:
                normalized = await _async_validate_input(self.hass, candidate)
            except AduroConnectionError:
                errors["base"] = "cannot_connect"
            except AduroResponseError:
                errors["base"] = "invalid_auth"
            except AduroError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - config flows must not leak library errors
                LOGGER.exception("Unexpected error while validating Aduro options")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_HOST: normalized[CONF_HOST],
                        CONF_PIN: normalized[CONF_PIN],
                        CONF_SCAN_INTERVAL: normalized[CONF_SCAN_INTERVAL],
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema({**current, **(user_input or {})}),
            errors=errors,
        )
