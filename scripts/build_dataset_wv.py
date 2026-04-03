#!/usr/bin/env python3
"""Build a West Virginia dual-city tornado history dataset for the web map.

Processes SPC tornado CSV data for two study areas simultaneously:
  - Fayetteville, WV  (38.0512 N, -81.1070 W) — Fayette County, New River Gorge
  - Bridgeport, WV    (39.2965 N, -80.2513 W) — Harrison County, Clarksburg metro

Risk zones are computed independently for each city and stored under separate keys.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_CSV     = PROJECT_ROOT / "data" / "raw" / "spc_1950_2024_actual_tornadoes.csv"
OUT_JSON    = PROJECT_ROOT / "data" / "processed" / "wv_tornadoes_30y.json"

CITIES = [
    {
        "key": "fayetteville", "name": "Fayetteville, WV",
        "lat": 38.0512, "lon": -81.1070,
        # Strict 20-mile single-point radius — only events genuinely close to the city.
        "radius_miles": 20,
        # Grid span covers the 20-mile study circle with a small margin.
        "grid_lat_span": 0.32,
        "grid_lon_span": 0.40,
    },
    {
        "key": "bridgeport", "name": "Bridgeport, WV",
        "lat": 39.2965, "lon": -80.2513,
        # Strict 20-mile single-point radius.
        "radius_miles": 20,
        "grid_lat_span": 0.32,
        "grid_lon_span": 0.40,
    },
]

# ── Geographic region annotations ─────────────────────────────────────────────
# (lat_min, lat_max, lon_min, lon_max, short_name, explanation)
GEO_REGIONS_FAY = [
    (37.85, 38.20, -81.30, -80.88,
     "New River Gorge / Fayette Plateau",
     "The Fayetteville study area sits on a plateau averaging 1,600\u20131,900\u202fft, "
     "split by the New River Gorge which cuts 900\u20131,200\u202fft below the surface. "
     "This creates synergistic protection: (1) plateau elevation reduces the depth of the "
     "lowest 1\u202fkm of the atmosphere where tornadoes form; (2) gorge-edge terrain "
     "prevents any consistent surface-wind alignment needed for circulation maintenance; "
     "(3) rapid terrain-roughness changes continuously disrupt low-level inflow; and "
     "(4) cold-air drainage from gorge walls creates surface stability. No broad flat "
     "approach corridor exists in any direction. SPC data since 1950 confirms this is "
     "among the lowest tornado-density plateau areas in the eastern US."),
    (37.65, 38.38, -82.03, -81.42,
     "Kanawha Valley \u2014 Western Approach Corridor",
     "The Kanawha River is the only significant west-to-east terrain opening in the "
     "Fayetteville study zone. Charleston (at the valley's widest point) does receive "
     "periodic tornado threats from Ohio Valley storm systems, but valley walls rise "
     "400\u2013800\u202fft within 2\u20133 miles, creating intense surface friction. Storms "
     "that track through Charleston lose significant low-level shear by the time they "
     "reach the Fayette County line ~30 miles east. In the historical record, western-approach "
     "events that eventually show up near Oak Hill or Fayetteville all used this valley "
     "corridor as their entry route \u2014 it is the primary \u2018weakened path\u2019 vector "
     "into the Fayetteville study area."),
    (37.33, 37.88, -81.75, -81.25,
     "Raleigh / Coal River Valley",
     "A moderately dissected plateau at 1,000\u20131,800\u202fft cut by the Coal River "
     "drainage system running NW\u2013SE. The dominant ridge axes here trend NE\u2013SW, "
     "cross-oriented to typical SW\u2013NE tornado motion \u2014 a cross-orientation that "
     "provides measurable terrain blocking that aligned valley systems lack. Historical "
     "weak tornado events in Raleigh County follow river corridors rather than crossing "
     "ridgelines, and track lengths are typically shorter than equivalent-EF events in "
     "the adjacent Tennessee Valley. Net effect: moderate protection, but river corridors "
     "create localised higher-risk sub-zones."),
    (37.33, 37.82, -81.25, -80.38,
     "Mercer / Monroe High Plateau \u2014 Allegheny Divide",
     "Terrain here reaches 2,500\u20133,500\u202fft \u2014 among the highest in WV. The "
     "Allegheny divide acts as a true orographic barrier: storms originating from the "
     "SW lose most low-level inflow energy crossing this terrain before reaching the "
     "Blue Ridge front. SPC records back to 1950 show near-zero tornado touchdowns per "
     "decade in this region. Even extreme outbreak tornadoes rarely maintain ground "
     "contact above 2,500\u202fft for any significant distance, giving this area the "
     "strongest natural protection of any sub-zone in the Fayetteville study area."),
    (37.82, 38.50, -80.52, -80.19,
     "Greenbrier Valley \u2014 Relatively Most Exposed Zone",
     "The Greenbrier River valley runs NNW\u2013SSE at roughly 1,650\u20132,200\u202fft, with "
     "Lewisburg near its lowest section. While still well-protected compared to any "
     "Tennessee Valley benchmark, this is the relatively highest-exposure sub-area in "
     "the Fayetteville study zone for two reasons: (1) valley alignment partially matches "
     "NE-moving storm flow, reducing cross-orientation blocking; and (2) storms from the "
     "ESE \u2014 a rare but real WV setup \u2014 face the least terrain obstruction in "
     "this direction. The marginal exposure difference is visible in SPC track density, "
     "which is slightly elevated in the Greenbrier Valley vs. surrounding plateau zones."),
    (38.20, 38.77, -81.42, -80.52,
     "Gauley / Nicholas County Uplands",
     "Remote high plateau at 1,800\u20132,200\u202fft. The Gauley River headwaters create "
     "a maze of ridges in multiple orientations, providing the same terrain fragmentation "
     "as the New River Gorge but with even less access via open west-to-east corridors. "
     "Distance from warm moist low-level air sources is also a factor here \u2014 the "
     "combination of elevation, topographic complexity, and dry-air proximity makes "
     "tornado development extremely rare. This sub-zone rarely shows a SPC track of "
     "any EF rating in any decade of the historical record."),
]

GEO_REGIONS_BPT = [
    (39.18, 39.44, -80.42, -80.12,
     "Harrison County / Clarksburg\u2013Bridgeport Core",
     "The primary study area. The Clarksburg\u2013Bridgeport corridor sits at 900\u20131,100\u202fft "
     "in the West Fork of the Monongahela River valley \u2014 the most open terrain in the "
     "study zone. Of all sub-regions here, this valley most closely resembles Ohio Valley "
     "terrain characteristics: low rolling hills, modest elevation change, and open "
     "agricultural land on the valley floor. SPC records show the highest documented tornado "
     "frequency in the North-Central WV study zone concentrated here, primarily EF0\u2013EF1 "
     "events in April\u2013May. Northwest approach vectors from the Ohio Valley have the "
     "easiest terrain access through this valley, making NW-track storms the primary threat."),
    (39.38, 39.80, -80.58, -80.12,
     "Marion County Uplands",
     "Rolling hills at 1,000\u20131,400\u202fft extending north of Bridgeport toward Fairmont "
     "and Mannington. Storms approaching from the NW (Ohio Valley / Pittsburgh-track) "
     "find gradually increasing surface friction here but no dramatic single-ridge barrier. "
     "The WV\u2013PA state-line area north of this zone has lower elevation, so storms can "
     "reach northern Marion County with reasonable intensity before terrain effects fully "
     "engage. Track records show moderate WV-scale activity here, particularly for NW\u2013SE "
     "tracking MCS events which are less terrain-sensitive than classic supercells."),
    (39.50, 40.02, -80.20, -79.33,
     "Monongalia / Preston Counties \u2014 Allegheny Front Zone",
     "Morgantown sits at ~960\u202fft but terrain rises rapidly to >3,000\u202fft east toward "
     "the Allegheny Front \u2014 one of the most abrupt terrain transitions in the eastern US. "
     "This creates a sharp east-west gradient: western Monongalia County has moderate "
     "WV-scale tornado exposure; eastern Preston County is effectively shielded by some "
     "of the highest terrain in the study zone. Tornado probability east of the Allegheny "
     "Front is near-zero historically. The divide acts as a complete barrier to low-level "
     "warm-air inflow from the SE, preventing tornado-supporting thermodynamic profiles "
     "from establishing in the eastern half of this sub-region."),
    (38.58, 39.02, -80.22, -79.33,
     "Randolph County / Elkins \u2014 Tygart Valley",
     "Elkins sits in the Tygart Valley at ~1,950\u202fft \u2014 already at an elevation where "
     "the low-level inflow depth available to tornadoes is reduced. The surrounding "
     "Allegheny Highlands (Cheat Mountain, Spruce Knob at 4,863\u202fft) completely block "
     "storm approaches from the south and east. The only viable approach vector is from "
     "the NW via the narrow Tygart Valley corridor. This specific vector has produced "
     "occasional brief EF0\u2013EF1 events in the valley, but all documented examples have "
     "very short tracks (1\u20133 miles), consistent with terrain-forced rapid dissipation."),
    (38.58, 39.20, -81.17, -80.62,
     "Lewis / Braxton Counties \u2014 Central WV Transitional Zone",
     "Central WV hill country at 800\u20131,500\u202fft forms a transitional belt between the "
     "more-exposed NW corridor and the well-protected Allegheny highlands. Stonewall Jackson "
     "Lake and the Elk River headwaters create modest valley corridors that can channel weak "
     "storm systems from the Ohio Valley. Tornado probability here is higher than the "
     "Fayetteville study area but still dramatically lower than AL/TN Valley benchmarks. "
     "Most documented events are brief EF0 touchdowns in open hilltop terrain near storm "
     "anvil edges, often associated with MCS events rather than classic supercells."),
    (38.90, 39.42, -80.68, -79.65,
     "Upshur / Barbour County Hills",
     "Rolling Appalachian hills at 1,200\u20131,600\u202fft from Buckhannon NE toward Philippi. "
     "These ridges are cross-oriented to typical NW\u2013SE storm motion, providing meaningful "
     "blocking that aligned valley systems lack. Valley corridors between Buckhannon and "
     "Philippi have seen EF0\u2013EF1 events during major outbreak situations, indicating "
     "that terrain protection is real but not absolute under high-shear conditions. "
     "Strong MCS events with embedded tornadoes are a higher threat here than classic "
     "supercells, as MCS circulations are less sensitive to terrain roughness than "
     "the sustained surface inflow that supercells require."),
    (39.48, 40.02, -81.17, -80.62,
     "Wetzel / Doddridge Counties (NW Entry Sector)",
     "The NW portion of the Bridgeport study zone transitions toward Ohio Valley terrain: "
     "lower elevation (700\u20131,100\u202fft), wider valleys, and less complex topography than "
     "the eastern Allegheny zones. Tornado-producing storms from Ohio that penetrate into "
     "WV typically enter through this corridor before encountering significant friction. "
     "SPC track records show that the majority of WV tornado paths reaching Clarksburg\u2013"
     "Bridgeport originate from storm tracks entering WV through this NW sector. "
     "It is the primary \u2018open gateway\u2019 for Ohio Valley tornado events affecting "
     "North-Central WV \u2014 and explains why Bridgeport's risk, while still low by national "
     "standards, is higher than any Fayetteville sub-zone."),
]

DEFAULT_REGION_FAY = {
    "name": "Southern WV Appalachian Highlands",
    "why": ("Southern West Virginia is among the most topographically protected areas "
            "in the contiguous US. Dense ridges, deep gorges, and plateau terrain at "
            "1,500\u20132,500\u202fft suppress tornado development and limit track "
            "continuation compared to the open Tennessee Valley or Ohio plains."),
}

DEFAULT_REGION_BPT = {
    "name": "North-Central WV Appalachian Uplands",
    "why": ("North-central West Virginia sits at the western edge of the Allegheny "
            "Highlands. Still substantially protected compared to the Ohio Valley, "
            "but lower and less rugged terrain than the Fayetteville area allows "
            "occasional tornado intrusions, particularly from the northwest."),
}


def region_for_cell(lat: float, lon: float, regions: list, default: dict) -> dict:
    for lat_min, lat_max, lon_min, lon_max, name, why in regions:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return {"name": name, "why": why}
    return default


@dataclass
class TornadoEvent:
    tornado_id: int
    date: str
    year: int
    state: str
    magnitude: int
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    length_miles: float
    width_yards: int
    injuries: int
    fatalities: int


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3958.8
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def load_events() -> list[TornadoEvent]:
    events: list[TornadoEvent] = []
    with RAW_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            start_lat = parse_float(row.get("slat", "0"))
            start_lon = parse_float(row.get("slon", "0"))
            end_lat   = parse_float(row.get("elat", "0"))
            end_lon   = parse_float(row.get("elon", "0"))
            if end_lat == 0.0 or end_lon == 0.0:
                end_lat, end_lon = start_lat, start_lon
            if start_lat == 0.0 or start_lon == 0.0:
                continue
            events.append(TornadoEvent(
                tornado_id  = parse_int(row.get("om", "0")),
                date        = row.get("date", ""),
                year        = parse_int(row.get("yr", "0")),
                state       = row.get("st", ""),
                magnitude   = parse_int(row.get("mag", "0")),
                start_lat   = start_lat,
                start_lon   = start_lon,
                end_lat     = end_lat,
                end_lon     = end_lon,
                length_miles= parse_float(row.get("len", "0")),
                width_yards = parse_int(row.get("wid", "0")),
                injuries    = parse_int(row.get("inj", "0")),
                fatalities  = parse_int(row.get("fat", "0")),
            ))
    return events


def is_near_city(event: TornadoEvent, city: dict) -> bool:
    """Return True if the event start or end point is within city['radius_miles'] of
    the city center.  Strict single-point radius — no anchors, no exclusions.
    """
    radius = city["radius_miles"]
    clat   = city["lat"]
    clon   = city["lon"]
    return (
        haversine_miles(clat, clon, event.start_lat, event.start_lon) <= radius
        or haversine_miles(clat, clon, event.end_lat, event.end_lon) <= radius
    )


def interpolate_track(event: TornadoEvent, sample_miles: float = 0.5) -> list[tuple[float, float]]:
    track_len = haversine_miles(event.start_lat, event.start_lon, event.end_lat, event.end_lon)
    if track_len < sample_miles:
        return [(event.start_lat, event.start_lon)]
    n = max(2, int(math.ceil(track_len / sample_miles)) + 1)
    return [
        (event.start_lat + i / (n - 1) * (event.end_lat  - event.start_lat),
         event.start_lon + i / (n - 1) * (event.end_lon  - event.start_lon))
        for i in range(n)
    ]


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[int(q * (len(ordered) - 1))]


def build_risk_zones(city: dict, events: list[TornadoEvent],
                     geo_regions: list, default_region: dict) -> list[dict]:
    """Build risk zone grid for a single city using its nearby event list."""
    step       = 0.02   # ~1.4 miles
    sigma_mi   = 2.5    # tight: zones follow actual valley corridors and track locations

    lat_c     = city["lat"]
    lon_c     = city["lon"]
    lat_span  = city.get("grid_lat_span", 0.72)
    lon_span  = city.get("grid_lon_span", 0.92)
    lat_min   = round(lat_c - lat_span, 6)
    lat_max   = round(lat_c + lat_span, 6)
    lon_min   = round(lon_c - lon_span, 6)
    lon_max   = round(lon_c + lon_span, 6)

    two_sigma_sq = 2.0 * sigma_mi ** 2

    event_data = []
    for ev in events:
        samples    = interpolate_track(ev)
        mag_w      = (max(0, ev.magnitude) ** 2) + 1.0
        width_f    = math.sqrt(max(50, ev.width_yards) / 300.0)
        event_data.append((samples, mag_w * width_f))

    cells: list[dict] = []
    lat = lat_min
    while lat < lat_max - 1e-9:
        lon = lon_min
        while lon < lon_max - 1e-9:
            cx = lat + step / 2
            cy = lon + step / 2
            score = 0.0
            for samples, weight in event_data:
                tot = 0.0
                for slat, slon in samples:
                    d = haversine_miles(cx, cy, slat, slon)
                    tot += math.exp(-(d ** 2) / two_sigma_sq)
                score += weight * (tot / len(samples))
            cells.append({
                "bbox": [round(lon, 6), round(lat, 6),
                         round(lon + step, 6), round(lat + step, 6)],
                "score": round(score, 4),
            })
            lon = round(lon + step, 6)
        lat = round(lat + step, 6)

    scores  = [c["score"] for c in cells]
    nonzero = sorted(s for s in scores if s > 0)
    if nonzero:
        q1 = quantile(nonzero, 0.30)
        q2 = quantile(nonzero, 0.55)
        q3 = quantile(nonzero, 0.75)
        q4 = quantile(nonzero, 0.88)
    else:
        q1 = q2 = q3 = q4 = 0.0

    max_score = max(scores) if scores else 1.0
    log_max   = math.log1p(max_score)

    for c in cells:
        s = c["score"]
        if s == 0 or s <= q1:   level = "Least Dangerous"
        elif s <= q2:            level = "Low"
        elif s <= q3:            level = "Moderate"
        elif s <= q4:            level = "High"
        else:                    level = "Most Dangerous"
        c["level"]     = level
        c["scoreNorm"] = round(math.log1p(s) / log_max, 4) if log_max > 0 else 0.0
        cx = (c["bbox"][1] + c["bbox"][3]) / 2
        cy = (c["bbox"][0] + c["bbox"][2]) / 2
        c["region"] = region_for_cell(cx, cy, geo_regions, default_region)
        c["city"]    = city["key"]
    return cells


def main() -> None:
    all_events = load_events()
    if not all_events:
        raise RuntimeError("No tornado events found in source data.")

    latest_year = max(e.year for e in all_events)
    min_year    = latest_year - 29
    recent      = [e for e in all_events if e.year >= min_year]

    # Separate event lists per city (events can appear in both if near both)
    city_events: dict[str, list[TornadoEvent]] = {}
    for city in CITIES:
        city_events[city["key"]] = [e for e in recent if is_near_city(e, city)]

    # Union of all nearby events (deduplicated by id) for the shared tornadoes list
    seen_ids: set[int] = set()
    all_nearby: list[TornadoEvent] = []
    for city in CITIES:
        for e in city_events[city["key"]]:
            if e.tornado_id not in seen_ids:
                seen_ids.add(e.tornado_id)
                all_nearby.append(e)

    # Build risk zones per city
    risk_zones: dict[str, list[dict]] = {}
    for city in CITIES:
        regs   = GEO_REGIONS_FAY if city["key"] == "fayetteville" else GEO_REGIONS_BPT
        deflt  = DEFAULT_REGION_FAY if city["key"] == "fayetteville" else DEFAULT_REGION_BPT
        evts   = city_events[city["key"]]
        zones  = build_risk_zones(city, evts, regs, deflt)
        risk_zones[city["key"]] = zones
        levels = {}
        for z in zones:
            levels[z["level"]] = levels.get(z["level"], 0) + 1
        print(f"  {city['name']}: {len(evts)} events, {len(zones)} zone cells — {levels}")

    output = {
        "meta": {
            "generated_utc":  datetime.now(UTC).isoformat(),
            "source":         "data/raw/spc_1950_2024_actual_tornadoes.csv",
            "year_range":     [min_year, latest_year],
            "cities":         CITIES,
            "radius_miles":   {city["key"]: city["radius_miles"] for city in CITIES},
            "counts": {
                city["key"]: len(city_events[city["key"]]) for city in CITIES
            },
        },
        "places": [
            {"name": "Fayetteville, WV",  "lat": 38.0512, "lon": -81.1070},
            {"name": "Bridgeport, WV",    "lat": 39.2965, "lon": -80.2513},
            {"name": "Clarksburg, WV",    "lat": 39.2814, "lon": -80.3445},
            {"name": "Oak Hill, WV",      "lat": 37.9751, "lon": -81.1512},
            {"name": "Summersville, WV",  "lat": 38.2820, "lon": -80.8523},
            {"name": "Weston, WV",        "lat": 39.0367, "lon": -80.4676},
        ],
        "tornadoes": [
            {
                "id":           e.tornado_id,
                "date":         e.date,
                "year":         e.year,
                "state":        e.state,
                "magnitude":    e.magnitude,
                "start":        {"lat": e.start_lat, "lon": e.start_lon},
                "end":          {"lat": e.end_lat,   "lon": e.end_lon},
                "length_miles": e.length_miles,
                "width_yards":  e.width_yards,
                "injuries":     e.injuries,
                "fatalities":   e.fatalities,
            }
            for e in all_nearby
        ],
        "riskZones": risk_zones,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_JSON}")
    print(f"  Total unique events: {len(all_nearby)}")
    print(f"  Year range: {min_year}–{latest_year}")


if __name__ == "__main__":
    main()
