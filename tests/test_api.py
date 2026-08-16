"""Tests for the pyduro compatibility wrapper."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from pyduro.actions import STATUS_PARAMS

from custom_components.aduro.api import (
    AduroApi,
    AduroConnectionError,
    AduroResponseError,
    normalize_pin,
    normalize_serial,
)
from custom_components.aduro.models import AduroData


class FakeResponse:
    """Small pyduro response stand-in."""

    def __init__(self, payload: object, status: int = 0) -> None:
        self.payload = payload
        self.status = status

    def parse_payload(self) -> object:
        return self.payload


def status_response() -> FakeResponse:
    """Return a complete status payload in pyduro's positional format."""
    values = [str(index) for index, _key in enumerate(STATUS_PARAMS)]
    return FakeResponse(",".join(values))


class AduroApiTests(unittest.TestCase):
    """Verify error handling, parsing, and write behavior."""

    def setUp(self) -> None:
        self.api = AduroApi("192.0.2.10", "1234", "9876")

    def test_credentials_are_normalized_like_pyduro(self) -> None:
        self.assertEqual(normalize_serial("1234"), "001234")
        self.assertEqual(normalize_pin("9876"), "9876000000")
        self.assertEqual(self.api.serial, "001234")
        self.assertEqual(self.api.pin, "9876000000")

    @patch("custom_components.aduro.api.pyduro_raw.run", return_value=status_response())
    def test_status_payload_is_mapped_and_floatified(self, raw_run: object) -> None:
        result = self.api.get_status()
        self.assertEqual(result["boiler_temp"], 0.0)
        self.assertEqual(result["state"], float(tuple(STATUS_PARAMS).index("state")))
        self.assertEqual(len(result), len(STATUS_PARAMS))

    @patch("custom_components.aduro.api.pyduro_raw.run", return_value=None)
    def test_missing_status_response_raises_connection_error(self, raw_run: object) -> None:
        with self.assertRaises(AduroConnectionError):
            self.api.get_status()

    @patch(
        "custom_components.aduro.api.pyduro_raw.run",
        return_value=FakeResponse("ignored", status=2),
    )
    def test_status_error_is_not_treated_as_valid_data(self, raw_run: object) -> None:
        with self.assertRaises(AduroResponseError):
            self.api.get_status()

    @patch("custom_components.aduro.api.pyduro_raw.run", return_value=status_response())
    @patch("custom_components.aduro.api.pyduro_get.run")
    def test_poll_reads_all_entity_setting_groups(self, get_run: object, raw_run: object) -> None:
        get_run.side_effect = lambda **kwargs: FakeResponse(
            {"value": "12.5", "group": kwargs["path"].split(".")[0]}
        )
        result = self.api.poll()
        self.assertEqual(set(result.settings), {"boiler", "regulation", "auger"})
        self.assertEqual(result.settings["boiler"]["value"], 12.5)

    @patch("custom_components.aduro.api.pyduro_raw.run", return_value=status_response())
    @patch("custom_components.aduro.api.pyduro_get.run")
    def test_poll_retains_last_setting_group_on_failure(
        self,
        get_run: object,
        raw_run: object,
    ) -> None:
        def get_side_effect(**kwargs: object) -> FakeResponse | None:
            if kwargs["path"] == "regulation.*":
                return None
            return FakeResponse({"ok": "1"})

        get_run.side_effect = get_side_effect
        previous = AduroData(settings={"regulation": {"fixed_power": 50.0}})
        result = self.api.poll(previous)
        self.assertEqual(result.settings["regulation"]["fixed_power"], 50.0)

    @patch(
        "custom_components.aduro.api.pyduro_set.run",
        return_value=FakeResponse("OK"),
    )
    def test_set_value_passes_legacy_paths_unchanged(self, set_run: object) -> None:
        self.api.set_value("misc.start", "1")
        set_run.assert_called_once_with(
            "192.0.2.10",
            "001234",
            "9876000000",
            "misc.start",
            "1",
        )

    @patch(
        "custom_components.aduro.api.pyduro_set.run",
        return_value=FakeResponse("denied", status=4),
    )
    def test_set_value_surfaces_controller_errors(self, set_run: object) -> None:
        with self.assertRaises(AduroResponseError):
            self.api.set_value("misc.stop", "1")


if __name__ == "__main__":
    unittest.main()
