"""Synchronous pyduro wrapper used by the Aduro integration."""

from __future__ import annotations

import logging
from threading import Lock
from typing import Any

from pyduro.actions import STATUS_PARAMS
from pyduro.actions import get as pyduro_get
from pyduro.actions import raw as pyduro_raw
from pyduro.actions import set as pyduro_set

from .const import SETTING_GROUPS
from .models import AduroData

LOGGER = logging.getLogger(__name__)

# pyduro binds every request to UDP source port 1901. A process-wide lock is
# therefore required even when multiple config entries or executor threads exist.
_PYDURO_LOCK = Lock()


class AduroError(Exception):
    """Base exception for Aduro communication errors."""


class AduroConnectionError(AduroError):
    """Raised when the stove does not answer."""


class AduroResponseError(AduroError):
    """Raised when the stove returns an error status."""

    def __init__(self, action: str, status: int) -> None:
        super().__init__(f"{action} returned status {status}")
        self.status = status


class AduroProtocolError(AduroError):
    """Raised when a response cannot be interpreted."""


def normalize_serial(value: str) -> str:
    """Normalize a serial exactly as pyduro does on the wire."""
    return f"{str(value).strip():0>6.6}"


def normalize_pin(value: str) -> str:
    """Normalize a PIN exactly as pyduro does on the wire."""
    return f"{str(value).strip():0<10.10}"


def _coerce_value(value: Any) -> Any:
    """Match the legacy bridge's conversion of numeric strings to floats."""
    if not isinstance(value, str):
        return value
    try:
        return float(value)
    except ValueError:
        return value


def _checked_response(response: Any, action: str) -> Any:
    """Validate a pyduro response."""
    if response is None:
        raise AduroConnectionError(f"No response while requesting {action}")
    status = int(getattr(response, "status", 0))
    if status != 0:
        raise AduroResponseError(action, status)
    return response


class AduroApi:
    """Thread-safe access to one Aduro/NBE controller."""

    def __init__(self, host: str, serial: str, pin: str) -> None:
        self.host = str(host).strip()
        self.serial = normalize_serial(serial)
        self.pin = normalize_pin(pin)

    def get_status(self) -> dict[str, Any]:
        """Read the complete legacy function-11 status payload."""
        with _PYDURO_LOCK:
            return self._get_status_locked()

    def poll(self, previous: AduroData | None = None) -> AduroData:
        """Read all data required by the native entities.

        Status is mandatory. Individual settings groups are optional because
        controller firmware variants do not necessarily expose every group.
        Last known settings are retained when one optional query fails.
        """
        with _PYDURO_LOCK:
            status = self._get_status_locked()
            settings: dict[str, dict[str, Any]] = {}

            for group in SETTING_GROUPS:
                try:
                    settings[group] = self._get_settings_locked(group)
                except AduroError as err:
                    if previous and group in previous.settings:
                        settings[group] = dict(previous.settings[group])
                    LOGGER.debug("Unable to update Aduro settings group %s: %s", group, err)

            return AduroData(status=status, settings=settings)

    def set_value(self, path: str, value: Any) -> None:
        """Write one setting or action and validate the controller response."""
        with _PYDURO_LOCK:
            response = pyduro_set.run(
                self.host,
                self.serial,
                self.pin,
                path,
                value,
            )
            _checked_response(response, f"set {path}")

    def _get_status_locked(self) -> dict[str, Any]:
        response = _checked_response(
            pyduro_raw.run(
                burner_address=self.host,
                serial=self.serial,
                pin_code=self.pin,
                function_id=11,
                payload="*",
            ),
            "status",
        )
        payload = response.parse_payload()
        if not isinstance(payload, str):
            raise AduroProtocolError("Status payload is not a string")

        values = payload.split(",")
        keys = tuple(STATUS_PARAMS.keys())
        if not values or not values[0]:
            raise AduroProtocolError("Status payload is empty")

        return {
            key: _coerce_value(values[index])
            for index, key in enumerate(keys)
            if index < len(values)
        }

    def _get_settings_locked(self, group: str) -> dict[str, Any]:
        response = _checked_response(
            pyduro_get.run(
                burner_address=self.host,
                serial=self.serial,
                pin_code=self.pin,
                function_name="settings",
                path=f"{group}.*",
            ),
            f"settings/{group}",
        )
        payload = response.parse_payload()
        if not isinstance(payload, dict):
            raise AduroProtocolError(f"Settings payload for {group} is not a mapping")
        return {str(key): _coerce_value(value) for key, value in payload.items()}
