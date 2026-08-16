"""Tests for Aduro state conversion helpers."""

from __future__ import annotations

import unittest

from custom_components.aduro.models import as_float, as_int, is_heating, state_text


class AduroModelTests(unittest.TestCase):
    """Verify compatibility with the legacy MQTT templates."""

    def test_numeric_conversion(self) -> None:
        self.assertEqual(as_float("12.5"), 12.5)
        self.assertEqual(as_int("12.9"), 12)
        self.assertIsNone(as_float("not-a-number"))
        self.assertIsNone(as_int(None))

    def test_heating_state_matches_legacy_off_codes(self) -> None:
        for state in (13, 14, 20, 28):
            with self.subTest(state=state):
                self.assertFalse(is_heating({"state": state}))
        self.assertTrue(is_heating({"state": 5}))
        self.assertIsNone(is_heating({}))

    def test_human_readable_states_match_legacy_discovery(self) -> None:
        expected = {
            (14, 0): "Aus",
            (14, 6): "Aus eingeleitet",
            (2, 0): "Zündung eingeleitet",
            (4, 0): "Zündung verlängert",
            (32, 0): "Betrieb, Aufheizen",
            (5, 0): "Betrieb, Normal",
            (0, 0): "Betrieb, Warten",
            (6, 0): "Betrieb, Temperatur erreicht",
            (9, 0): "Angehalten, Holzverbrennung",
            (20, 0): "Angehalten, Flamme erloschen",
            (13, 0): "Angehalten, Zündung fehlgeschlagen",
            (28, 0): "Tür offen",
            (24, 0): "Pellet-Luftzufuhrhebel geschlossen",
        }
        for (state, substate), text in expected.items():
            with self.subTest(state=state, substate=substate):
                self.assertEqual(state_text({"state": state, "substate": substate}), text)

        self.assertEqual(state_text({"state": 14, "substate": 9}), "Unbekannt (14/9)")
        self.assertEqual(state_text({"state": 99}), "Unbekannt (99)")
        self.assertIsNone(state_text({}))


if __name__ == "__main__":
    unittest.main()
