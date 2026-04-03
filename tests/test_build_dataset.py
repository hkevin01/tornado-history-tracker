"""Tests for tornado dataset build helpers."""

import unittest

from scripts.build_dataset import (
    TornadoEvent,
    build_risk_zones,
    event_is_near_huntsville,
    haversine_miles,
    parse_float,
    parse_int,
)


class BuildDatasetTests(unittest.TestCase):
    """Validate core helper behavior for happy, edge, and error conditions."""

    def test_haversine_zero_distance(self):
        """Happy path: zero distance returns approximately zero miles."""
        self.assertAlmostEqual(haversine_miles(34.7, -86.5, 34.7, -86.5), 0.0, places=3)

    def test_parse_int_error_condition(self):
        """Error path: invalid integer text falls back to default."""
        self.assertEqual(parse_int("not-a-number", default=7), 7)

    def test_parse_float_error_condition(self):
        """Error path: invalid float text falls back to default."""
        self.assertEqual(parse_float("oops", default=3.25), 3.25)

    def test_event_near_huntsville_edge(self):
        """Edge path: near event should be included, distant event excluded."""
        near = TornadoEvent(1, "2020-01-01", 2020, "AL", 1, 34.73, -86.58, 34.74, -86.57, 1.0, 20, 0, 0)
        far = TornadoEvent(2, "2020-01-01", 2020, "AL", 1, 33.0, -88.0, 33.1, -88.1, 1.0, 20, 0, 0)
        self.assertTrue(event_is_near_huntsville(near))
        self.assertFalse(event_is_near_huntsville(far))

    def test_build_risk_zones_happy(self):
        """Happy path: risk zones are produced with level labels."""
        events = [
            TornadoEvent(1, "2023-03-01", 2023, "AL", 3, 34.75, -86.60, 34.80, -86.55, 5.0, 150, 2, 0),
            TornadoEvent(2, "2019-04-02", 2019, "AL", 1, 34.68, -86.50, 34.71, -86.48, 2.0, 60, 0, 0),
        ]
        zones = build_risk_zones(events)
        self.assertGreater(len(zones), 0)
        self.assertIn("level", zones[0])
        levels = {z["level"] for z in zones}
        self.assertTrue(levels.intersection({"Least Dangerous", "Low", "Moderate", "High", "Most Dangerous"}))


if __name__ == "__main__":
    unittest.main()
