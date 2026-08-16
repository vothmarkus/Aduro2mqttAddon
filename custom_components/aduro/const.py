"""Constants for the Aduro integration."""

from __future__ import annotations

DOMAIN = "aduro"

CONF_SERIAL = "serial"
CONF_PIN = "pin"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_NAME = "name"

DEFAULT_NAME = "Aduro H2"
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300
COMMAND_REFRESH_DELAY = 0.6

PLATFORMS = ("climate", "number", "select", "sensor", "switch")

OFF_STATE_CODES = frozenset({13, 14, 20, 28})
SETTING_GROUPS = ("boiler", "regulation", "auger")
