"""Tests for WV dual-city tornado dataset build helpers."""

import unittest

from scripts.build_dataset_wv import (
    CITIES,
    DEFAULT_REGION_BPT,
    DEFAULT_REGION_FAY,
    GEO_REGIONS_BPT,
    GEO_REGIONS_FAY,
    TornadoEvent,
    build_risk_zones,
    haversine_miles,
    interpolate_track,
    is_near_city,
    parse_float,
    parse_int,
    region_for_cell,
)


class WVHaversineTests(unittest.TestCase):
    """Validate haversine distance helper."""

    def test_zero_distance(self):
        """Happy path: same point returns ~0 miles."""
        self.assertAlmostEqual(haversine_miles(38.0512, -81.107, 38.0512, -81.107), 0.0, places=3)

    def test_known_distance_fay_to_bpt(self):
        """Happy path: Fayetteville to Bridgeport is approximately 86 miles straight-line."""
        d = haversine_miles(38.0512, -81.107, 39.2965, -80.2513)
        self.assertGreater(d, 80)
        self.assertLess(d, 100)


class WVParseTests(unittest.TestCase):
    """Validate numeric parsing helpers."""

    def test_parse_int_valid(self):
        """Happy path: valid integer string."""
        self.assertEqual(parse_int("3"), 3)

    def test_parse_int_invalid(self):
        """Error path: non-numeric falls back to default."""
        self.assertEqual(parse_int("bad", default=5), 5)

    def test_parse_float_valid(self):
        """Happy path: valid float string."""
        self.assertAlmostEqual(parse_float("1.5"), 1.5)

    def test_parse_float_invalid(self):
        """Error path: non-numeric falls back to default."""
        self.assertAlmostEqual(parse_float("nope", default=2.0), 2.0)


class WVInterpolateTrackTests(unittest.TestCase):
    """Validate track interpolation helper."""

    def test_short_track_returns_start(self):
        """Edge path: track shorter than sample distance returns start point."""
        ev = TornadoEvent(1, "2020-01-01", 2020, "WV", 0,
                          38.05, -81.10, 38.051, -81.101, 0.1, 50, 0, 0)
        pts = interpolate_track(ev, sample_miles=1.0)
        self.assertEqual(len(pts), 1)
        self.assertAlmostEqual(pts[0][0], 38.05)

    def test_long_track_has_multiple_points(self):
        """Happy path: 10-mile track produces multiple interpolated points."""
        ev = TornadoEvent(2, "2021-05-01", 2021, "WV", 1,
                          38.00, -81.20, 38.14, -81.00, 10.0, 100, 0, 0)
        pts = interpolate_track(ev, sample_miles=1.0)
        self.assertGreater(len(pts), 5)


class WVIsNearCityTests(unittest.TestCase):
    """Validate multi-anchor city proximity detection."""

    def _make_event(self, slat, slon, elat=None, elon=None, mag=0):
        if elat is None:
            elat, elon = slat, slon
        return TornadoEvent(99, "2010-04-01", 2010, "WV", mag,
                            slat, slon, elat, elon, 0.5, 50, 0, 0)

    def test_event_at_fayetteville_center_is_near(self):
        """Happy path: event at Fayetteville city center is within study area."""
        fay_city = next(c for c in CITIES if c["key"] == "fayetteville")
        ev = self._make_event(38.0512, -81.1070)
        self.assertTrue(is_near_city(ev, fay_city))

    def test_event_at_bridgeport_center_is_near(self):
        """Happy path: event at Bridgeport city center is within study area."""
        bpt_city = next(c for c in CITIES if c["key"] == "bridgeport")
        ev = self._make_event(39.2965, -80.2513)
        self.assertTrue(is_near_city(ev, bpt_city))

    def test_distant_event_is_not_near_fayetteville(self):
        """Edge path: event in western Ohio is not near Fayetteville."""
        fay_city = next(c for c in CITIES if c["key"] == "fayetteville")
        ev = self._make_event(39.96, -82.99)
        self.assertFalse(is_near_city(ev, fay_city))

    def test_distant_event_is_not_near_bridgeport(self):
        """Edge path: event in central Kentucky is not near Bridgeport."""
        bpt_city = next(c for c in CITIES if c["key"] == "bridgeport")
        ev = self._make_event(37.84, -85.48)
        self.assertFalse(is_near_city(ev, bpt_city))

    def test_event_just_outside_radius_excluded(self):
        """Edge path: event 21+ miles from Fayetteville center is excluded."""
        fay_city = next(c for c in CITIES if c["key"] == "fayetteville")
        # ~21 miles due west of Fayetteville center (lon=-81.50)
        ev = self._make_event(38.0512, -81.50)
        self.assertFalse(is_near_city(ev, fay_city))

    def test_event_just_inside_radius_included(self):
        """Edge path: event ~18 miles from Bridgeport center is included."""
        bpt_city = next(c for c in CITIES if c["key"] == "bridgeport")
        # ~15 miles north of Bridgeport
        ev = self._make_event(39.52, -80.25)
        self.assertTrue(is_near_city(ev, bpt_city))


class WVRegionAnnotationTests(unittest.TestCase):
    """Validate geographic region lookup for risk-zone cells."""

    def test_fayetteville_core_region_found(self):
        """Happy path: cell at Fayetteville center resolves to a named FAY region."""
        region = region_for_cell(38.05, -81.10, GEO_REGIONS_FAY, DEFAULT_REGION_FAY)
        self.assertIn("name", region)
        self.assertNotEqual(region["name"], DEFAULT_REGION_FAY["name"])

    def test_bridgeport_core_region_found(self):
        """Happy path: cell at Bridgeport center resolves to a named BPT region."""
        region = region_for_cell(39.30, -80.28, GEO_REGIONS_BPT, DEFAULT_REGION_BPT)
        self.assertIn("name", region)
        self.assertNotEqual(region["name"], DEFAULT_REGION_BPT["name"])

    def test_out_of_bounds_uses_default(self):
        """Edge path: cell outside all named regions falls back to the default."""
        region = region_for_cell(45.0, -75.0, GEO_REGIONS_FAY, DEFAULT_REGION_FAY)
        self.assertEqual(region["name"], DEFAULT_REGION_FAY["name"])

    def test_region_has_why_field(self):
        """Happy path: every region including default has a non-empty 'why' explanation."""
        region = region_for_cell(38.05, -81.10, GEO_REGIONS_FAY, DEFAULT_REGION_FAY)
        self.assertIn("why", region)
        self.assertGreater(len(region["why"]), 20)


class WVBuildRiskZonesTests(unittest.TestCase):
    """Validate risk zone grid generation for WV cities."""

    def _make_events(self):
        return [
            TornadoEvent(1, "2023-03-01", 2023, "WV", 2,
                         38.05, -81.10, 38.08, -81.07, 3.0, 100, 1, 0),
            TornadoEvent(2, "2019-04-15", 2019, "WV", 1,
                         38.02, -81.05, 38.04, -81.02, 1.5, 60, 0, 0),
        ]

    def test_risk_zones_produced(self):
        """Happy path: build_risk_zones returns non-empty list for Fayetteville."""
        fay_city = next(c for c in CITIES if c["key"] == "fayetteville")
        zones = build_risk_zones(fay_city, self._make_events(), GEO_REGIONS_FAY, DEFAULT_REGION_FAY)
        self.assertGreater(len(zones), 0)

    def test_zone_has_required_keys(self):
        """Happy path: every zone cell has bbox, score, level, scoreNorm, region, city."""
        fay_city = next(c for c in CITIES if c["key"] == "fayetteville")
        zones = build_risk_zones(fay_city, self._make_events(), GEO_REGIONS_FAY, DEFAULT_REGION_FAY)
        required = {"bbox", "score", "level", "scoreNorm", "region", "city"}
        for zone in zones[:10]:  # spot check first 10 cells
            self.assertTrue(required.issubset(zone.keys()), f"Missing keys in zone: {zone.keys()}")

    def test_zone_levels_are_valid(self):
        """Happy path: all risk levels are one of the five expected labels."""
        fay_city = next(c for c in CITIES if c["key"] == "fayetteville")
        zones = build_risk_zones(fay_city, self._make_events(), GEO_REGIONS_FAY, DEFAULT_REGION_FAY)
        valid = {"Least Dangerous", "Low", "Moderate", "High", "Most Dangerous"}
        for z in zones:
            self.assertIn(z["level"], valid)

    def test_zone_city_key_matches(self):
        """Happy path: zone city field matches the city key used to build it."""
        fay_city = next(c for c in CITIES if c["key"] == "fayetteville")
        zones = build_risk_zones(fay_city, self._make_events(), GEO_REGIONS_FAY, DEFAULT_REGION_FAY)
        for z in zones[:10]:
            self.assertEqual(z["city"], "fayetteville")

    def test_empty_event_list_produces_zones(self):
        """Edge path: zero events produces zones all at Least Dangerous level."""
        fay_city = next(c for c in CITIES if c["key"] == "fayetteville")
        zones = build_risk_zones(fay_city, [], GEO_REGIONS_FAY, DEFAULT_REGION_FAY)
        self.assertGreater(len(zones), 0)
        levels = {z["level"] for z in zones}
        self.assertEqual(levels, {"Least Dangerous"})

    def test_score_norm_is_between_0_and_1(self):
        """Happy path: scoreNorm values are in [0, 1] range."""
        fay_city = next(c for c in CITIES if c["key"] == "fayetteville")
        zones = build_risk_zones(fay_city, self._make_events(), GEO_REGIONS_FAY, DEFAULT_REGION_FAY)
        for z in zones:
            self.assertGreaterEqual(z["scoreNorm"], 0.0)
            self.assertLessEqual(z["scoreNorm"], 1.0)


if __name__ == "__main__":
    unittest.main()
