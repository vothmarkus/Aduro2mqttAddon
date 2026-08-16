"""Data models and state helpers for the Aduro integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import OFF_STATE_CODES


@dataclass(frozen=True, slots=True)
class AduroData:
    """Latest data received from one stove."""

    status: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, dict[str, Any]] = field(default_factory=dict)

    def setting(self, group: str, key: str, default: Any = None) -> Any:
        """Return a setting value."""
        return self.settings.get(group, {}).get(key, default)


def as_float(value: Any) -> float | None:
    """Convert an Aduro value to float when possible."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    """Convert an Aduro value to int when possible."""
    converted = as_float(value)
    return None if converted is None else int(converted)


def is_heating(status: dict[str, Any]) -> bool | None:
    """Mirror the legacy heating switch state calculation."""
    state = as_int(status.get("state"))
    if state is None:
        return None
    return state not in OFF_STATE_CODES


def state_text(status: dict[str, Any]) -> str | None:
    """Mirror the human-readable state from the MQTT discovery template."""
    state = as_int(status.get("state"))
    substate = as_int(status.get("substate"))

    if state is None:
        return None
    if state == 14:
        if substate == 0:
            return "Aus"
        if substate == 6:
            return "Aus eingeleitet"
        return f"Unbekannt (14/{substate if substate is not None else '?'})"

    states = {
        0: "Betrieb, Warten",
        2: "Zündung eingeleitet",
        4: "Zündung verlängert",
        5: "Betrieb, Normal",
        6: "Betrieb, Temperatur erreicht",
        9: "Angehalten, Holzverbrennung",
        13: "Angehalten, Zündung fehlgeschlagen",
        20: "Angehalten, Flamme erloschen",
        24: "Pellet-Luftzufuhrhebel geschlossen",
        28: "Tür offen",
        32: "Betrieb, Aufheizen",
    }
    return states.get(state, f"Unbekannt ({state})")
