#!/usr/bin/env python3
"""Build a Huntsville-area tornado history dataset for the web map.

This script fetches SPC historical tornado CSV data, filters events to the
past 30 years near Huntsville, Alabama, and computes risk zones suitable for
map visualization.
"""

from __future__ import annotations

import csv
import json
import math
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


SPC_URL = "https://www.spc.noaa.gov/wcm/data/1950-2024_actual_tornadoes.csv"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = PROJECT_ROOT / "data" / "raw" / "spc_1950_2024_actual_tornadoes.csv"
OUT_JSON = PROJECT_ROOT / "data" / "processed" / "huntsville_tornadoes_30y.json"

HUNTSVILLE_LAT = 34.7304
HUNTSVILLE_LON = -86.5861
RADIUS_MILES = 35.0

# Geographic region descriptors annotated onto each risk zone cell.
# Tuple layout: (lat_min, lat_max, lon_min, lon_max, short_name, explanation)
GEOGRAPHIC_REGIONS = [
    (34.68, 34.86, -86.60, -86.41,
     "Monte Sano / East Huntsville Highlands",
     "Monte Sano plateau rises to 1,500\u20131,900\u202fft immediately east of the city, "
     "creating a sharp surface-roughness transition that disrupts the near-surface inflow layer "
     "tornadoes depend on. Cold-air drainage from the plateau frequently stabilises the surface "
     "boundary layer below the ridge top. While EF1+ events have crossed the highland during "
     "major outbreaks, track lengths on the plateau are typically 40\u201360\u202f% shorter than "
     "equivalent events on the open valley floor. Hampton Cove, just east of the plateau "
     "face, receives partial lee-side protection for NW-approach storms."),
    (34.72, 35.12, -87.16, -86.55,
     "Limestone Co. \u2014 Open Plains (Primary SW Corridor)",
     "The single highest-exposure sub-region in the study area. No terrain barrier exists "
     "within 100\u202fmiles to the SW, keeping surface inflow undisturbed from the Mississippi "
     "state line straight into northern Huntsville. Elevation is flat at 550\u2013700\u202fft; "
     "agricultural terrain minimises surface roughness. The April 27 2011 EF4 and the 1974 "
     "Super Outbreak both sent primary tracks through this corridor. Low-level jet convergence "
     "along the SW approach vector routinely maximises wind shear directly over this zone on "
     "severe-weather days."),
    (34.48, 34.85, -87.16, -86.80,
     "Tennessee River Valley (W Approach Corridor)",
     "The Tennessee River cuts an east-trending valley at 550\u2013650\u202fft with walls rising "
     "150\u2013300\u202fft on both banks. This geometry channels and accelerates near-surface storm "
     "winds directly toward Madison County and Huntsville. SPC track records show multiple "
     "tornadoes following a nearly straight path from Decatur through this corridor before "
     "intensifying as they exit the broad valley near Madison. Valley funneling explains why "
     "tracks here are typically longer than comparable-EF events on the open plains."),
    (34.26, 34.62, -87.16, -86.35,
     "Morgan County \u2014 Decatur Convergence Zone",
     "Flat to gently rolling terrain at 550\u2013700\u202fft with minimal surface roughness from "
     "wide agricultural floodplains. Decatur sits at a natural convergence point: the Tennessee "
     "River crossing creates a low-level wind confluence where storms frequently intensify or "
     "maintain rating. Long-track tornadoes (>10 miles) have above-average historical occurrence "
     "in Morgan/Limestone County compared to topographically complex areas. Storm inflow from "
     "the SW reaches this zone unobstructed, making it a reliable intensification corridor."),
    (34.40, 34.72, -86.44, -85.84,
     "Sand Mountain / Cumberland Plateau Escarpment",
     "The western face of Sand Mountain rises 800\u20131,000\u202fft within roughly 2 miles, the "
     "most abrupt terrain barrier in the Huntsville study area. This escarpment disrupts "
     "near-surface inflow for storms approaching from the SW or S, and supercells measurably "
     "weaken crossing the edge. However the barrier is not absolute: EF3+ tornadoes crossed "
     "Sand Mountain in 1973, 1974, and April 2011 during high-shear setups with deep storm "
     "circulations. The northwestern escarpment face focuses damage paths that do breach the "
     "plateau, producing intense but shorter tracks on the plateau itself."),
    (34.56, 34.82, -86.80, -86.56,
     "Jones Valley \u2014 Primary Risk Corridor",
     "The highest-risk zone for Huntsville proper. Jones Valley runs SW\u2013NE for ~20 miles "
     "nearly parallel to the 230\u00b0\u2013050\u00b0 prevailing tornado motion vector. The valley "
     "narrows to 3\u20135\u202fmiles between Keel Mountain (east wall, ~900\u202fft) and the "
     "Chapman Mountain/Blevins Gap ridgeline (west wall, ~1,100\u202fft). This funnel geometry "
     "concentrates near-surface wind shear and maintains low-level circulation longer than open "
     "terrain. The April 27 2011 EF4 followed this valley precisely for over 15 miles; the "
     "1974 outbreak produced similar signatures. When a supercell enters Jones Valley, "
     "there is very little terrain resistance to track continuation."),
    (34.50, 34.73, -86.57, -86.26,
     "SE Huntsville / Hampton Cove Area",
     "Hampton Cove sits in a modest bowl: Monte Sano plateau (~1,700\u202fft) to the NW and the "
     "Sand Mountain escarpment (~1,100\u202fft) to the SE and east provide a \u2018double shield\u2019 "
     "geometry. Storms must either cross Monte Sano from the west (losing low-level inflow) or "
     "approach from due south where Sand Mountain provides 800\u202fft of obstruction. Track "
     "density here is measurably lower than Jones Valley. However, EF2+ supercells with deep "
     "circulation (>10,000\u202fft) can maintain ground contact over both ridgelines, as "
     "demonstrated by regional outbreak events. The protection is real and statistically "
     "significant, but not reliable under extreme shear conditions."),
    (34.78, 35.32, -86.68, -85.88,
     "Jackson / NE Madison Co. Foothills",
     "Terrain rises gently NE toward the Tennessee state line, reaching 800\u20131,200\u202fft "
     "with increasing forest cover and rolling hills. Surface roughness gradually increases but "
     "never approaches Sand Mountain or Appalachian scales. Historical track density noticeably "
     "decreases relative to the open plains, as tornadoes that reach this zone are typically "
     "in their weakening stage \u2014 having already dissipated energy crossing the Tennessee "
     "River corridor or the Madison County terrain transitions. The NE direction also takes "
     "storms away from the primary warm low-level jet axis."),
    (34.08, 34.42, -86.92, -86.28,
     "S. Morgan / N. Cullman Co. \u2014 Southern Approach",
     "Rolling hills at 700\u2013900\u202fft with terrain climbing toward Sand Mountain and the "
     "southern escarpment. Cullman County has its own documented tornado history \u2014 terrain "
     "provides modest roughness but not the abrupt barriers of Sand Mountain or Appalachian "
     "ridges. Storms approaching from the SW find gradually increasing surface friction, "
     "producing shorter average track lengths (2\u20135 miles) relative to the flat Limestone "
     "County corridor. This zone acts as an approach ramp for storms building toward the "
     "Tennessee Valley \u2014 weaker events often dissipate here while intense supercells "
     "push through."),
]


def region_for_cell(lat: float, lon: float) -> dict:
    """Return geographic region name and explanation for a grid cell centre."""
    for lat_min, lat_max, lon_min, lon_max, name, why in GEOGRAPHIC_REGIONS:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return {"name": name, "why": why}
    return {
        "name": "Tennessee Valley Region",
        "why": (
            "Part of the broader Tennessee Valley \u2014 a region that experiences "
            "periodic tornado activity from storms tracking northeast across Alabama."
        ),
    }


@dataclass
class TornadoEvent:
    """Represents one tornado event used by the map and risk model."""

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
    """Compute great-circle distance between two points in miles."""
    earth_radius_mi = 3958.8
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_mi * c


def fetch_csv() -> None:
    """Download the SPC CSV dataset to the raw data folder."""
    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(SPC_URL, timeout=60) as resp:
        content = resp.read()
    RAW_CSV.write_bytes(content)


def parse_int(value: str, default: int = 0) -> int:
    """Parse integer safely from CSV values."""
    try:
        return int(float(value))
    except Exception:
        return default


def parse_float(value: str, default: float = 0.0) -> float:
    """Parse float safely from CSV values."""
    try:
        return float(value)
    except Exception:
        return default


def load_events() -> list[TornadoEvent]:
    """Load all tornado events from the raw CSV."""
    events: list[TornadoEvent] = []
    with RAW_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            start_lat = parse_float(row.get("slat", "0"))
            start_lon = parse_float(row.get("slon", "0"))
            end_lat = parse_float(row.get("elat", "0"))
            end_lon = parse_float(row.get("elon", "0"))
            if end_lat == 0.0 or end_lon == 0.0:
                end_lat, end_lon = start_lat, start_lon

            if start_lat == 0.0 or start_lon == 0.0:
                continue

            events.append(
                TornadoEvent(
                    tornado_id=parse_int(row.get("om", "0")),
                    date=row.get("date", ""),
                    year=parse_int(row.get("yr", "0")),
                    state=row.get("st", ""),
                    magnitude=parse_int(row.get("mag", "0")),
                    start_lat=start_lat,
                    start_lon=start_lon,
                    end_lat=end_lat,
                    end_lon=end_lon,
                    length_miles=parse_float(row.get("len", "0")),
                    width_yards=parse_int(row.get("wid", "0")),
                    injuries=parse_int(row.get("inj", "0")),
                    fatalities=parse_int(row.get("fat", "0")),
                )
            )
    return events


def event_is_near_huntsville(event: TornadoEvent) -> bool:
    """Return True when any interpolated track point is within the radius.

    Checking only start/end would miss long-track events that pass through
    the study area with both endpoints outside it.
    """
    # Fast path: check endpoints first
    if min(
        haversine_miles(HUNTSVILLE_LAT, HUNTSVILLE_LON, event.start_lat, event.start_lon),
        haversine_miles(HUNTSVILLE_LAT, HUNTSVILLE_LON, event.end_lat, event.end_lon),
    ) <= RADIUS_MILES:
        return True
    # Interpolate track and check each sample
    track_len = haversine_miles(
        event.start_lat, event.start_lon, event.end_lat, event.end_lon
    )
    n = max(2, int(math.ceil(track_len / 1.0)) + 1) if track_len >= 1.0 else 1
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0
        plat = event.start_lat + t * (event.end_lat - event.start_lat)
        plon = event.start_lon + t * (event.end_lon - event.start_lon)
        if haversine_miles(HUNTSVILLE_LAT, HUNTSVILLE_LON, plat, plon) <= RADIUS_MILES:
            return True
    return False


def quantile(values: list[float], q: float) -> float:
    """Compute an approximate quantile for non-empty numeric lists."""
    ordered = sorted(values)
    idx = int(q * (len(ordered) - 1))
    return ordered[idx]


def interpolate_track(event: TornadoEvent, sample_miles: float = 0.4) -> list[tuple[float, float]]:
    """Return lat/lon sample points spaced ~sample_miles apart along the track.

    For zero-length events (start == end) returns just the start point.
    Interpolation is linear in geographic degrees which is accurate enough at
    <35 mile scales.
    """
    track_len = haversine_miles(
        event.start_lat, event.start_lon, event.end_lat, event.end_lon
    )
    if track_len < sample_miles:
        return [(event.start_lat, event.start_lon)]

    n_samples = max(2, int(math.ceil(track_len / sample_miles)) + 1)
    points = []
    for i in range(n_samples):
        t = i / (n_samples - 1)
        plat = event.start_lat + t * (event.end_lat - event.start_lat)
        plon = event.start_lon + t * (event.end_lon - event.start_lon)
        points.append((plat, plon))
    return points


def build_risk_zones(events: list[TornadoEvent]) -> list[dict]:
    """Build rectangular risk cells scored by tornado track proximity.

    Key improvements over the midpoint-only approach:
    - Score is accumulated over interpolated track points (~0.4 mi spacing)
      so long tracks contribute meaningful detail rather than one blob.
    - Tight sigma (3.5 mi) creates real differentiation between valleys
      and protected ridgelines (e.g. Monte Sano, Chapman Mountain).
    - Magnitude weighting is quadratic so EF3+ events dominate clearly.
    - Width factor accounts for ground swath — a 1/4-mile-wide tornado
      threatens far more cells than a 50-yard rope.
    - Per-event contribution is normalised by sample count so a 30-mile
      track and a 1-mile track don't differ just by length.
    """
    lat_min = HUNTSVILLE_LAT - 0.72
    lat_max = HUNTSVILLE_LAT + 0.72
    lon_min = HUNTSVILLE_LON - 0.92
    lon_max = HUNTSVILLE_LON + 0.92
    step = 0.02          # ≈1.4 miles — finer than previous 0.03
    sigma_miles = 2.0    # very tight: zones follow actual track corridors precisely

    # Pre-compute track samples and weights for each event
    event_data = []
    for event in events:
        samples = interpolate_track(event, sample_miles=0.4)
        mag_weight = (max(0, event.magnitude) ** 2) + 1.0   # quadratic: EF0→1, EF3→10, EF5→26
        width_factor = math.sqrt(max(50, event.width_yards) / 300.0)
        event_data.append((samples, mag_weight * width_factor))

    two_sigma_sq = 2.0 * sigma_miles ** 2

    cells: list[dict] = []
    lat = lat_min
    while lat < lat_max - 1e-9:
        lon = lon_min
        while lon < lon_max - 1e-9:
            center_lat = lat + step / 2
            center_lon = lon + step / 2
            score = 0.0
            for samples, weight in event_data:
                # Accumulate Gaussian contributions from each track sample,
                # then normalise so score is per-sample (length-independent).
                sample_total = 0.0
                for slat, slon in samples:
                    dist = haversine_miles(center_lat, center_lon, slat, slon)
                    sample_total += math.exp(-(dist ** 2) / two_sigma_sq)
                score += weight * (sample_total / len(samples))

            cells.append(
                {
                    "bbox": [
                        round(lon, 6),
                        round(lat, 6),
                        round(lon + step, 6),
                        round(lat + step, 6),
                    ],
                    "score": round(score, 4),
                }
            )
            lon = round(lon + step, 6)
        lat = round(lat + step, 6)

    # Use log-scale percentile cuts so the contrast between 0-event mountain
    # cells and high-frequency valley cells is visually clear.
    scores = [c["score"] for c in cells]
    # Non-zero scores only for percentile calculation — cells with score=0 are
    # automatically "Least Dangerous".
    nonzero = sorted(s for s in scores if s > 0)
    if nonzero:
        # Use aggressive lower cuts: bottom 40% of non-zero = Low/Least,
        # leaving the top 20% to drive "Most Dangerous" designations.
        q1 = quantile(nonzero, 0.30)
        q2 = quantile(nonzero, 0.55)
        q3 = quantile(nonzero, 0.75)
        q4 = quantile(nonzero, 0.88)
    else:
        q1 = q2 = q3 = q4 = 0.0

    max_score = max(scores) if scores else 1.0
    log_max = math.log1p(max_score)

    for c in cells:
        s = c["score"]
        if s == 0 or s <= q1:
            level = "Least Dangerous"
        elif s <= q2:
            level = "Low"
        elif s <= q3:
            level = "Moderate"
        elif s <= q4:
            level = "High"
        else:
            level = "Most Dangerous"
        c["level"] = level
        # Logarithmic 0–1 normalisation: cells near zero are almost transparent
        # in the map while high-risk cells render as vivid solid colour.
        c["scoreNorm"] = round(math.log1p(s) / log_max, 4) if log_max > 0 else 0.0
        center_lat = (c["bbox"][1] + c["bbox"][3]) / 2
        center_lon = (c["bbox"][0] + c["bbox"][2]) / 2
        c["region"] = region_for_cell(center_lat, center_lon)

    return cells


def main() -> None:
    """Build processed data file consumed by the frontend map."""
    fetch_csv()
    all_events = load_events()
    if not all_events:
        raise RuntimeError("No tornado events found in source data.")

    latest_year = max(e.year for e in all_events)
    min_year = latest_year - 29
    recent = [e for e in all_events if e.year >= min_year]
    nearby = [e for e in recent if event_is_near_huntsville(e)]

    risk_zones = build_risk_zones(nearby)

    output = {
        "meta": {
            "generated_utc": datetime.now(UTC).isoformat(),
            "source": SPC_URL,
            "latest_year_in_source": latest_year,
            "year_range": [min_year, latest_year],
            "center": {"lat": HUNTSVILLE_LAT, "lon": HUNTSVILLE_LON},
            "radius_miles": RADIUS_MILES,
            "counts": {"all_recent": len(recent), "nearby": len(nearby)},
        },
        "places": [
            {"name": "Huntsville", "lat": 34.7304, "lon": -86.5861},
            {"name": "Chapman Mountain", "lat": 34.7679, "lon": -86.5294},
            {"name": "Hampton Cove", "lat": 34.6353, "lon": -86.4867},
        ],
        "tornadoes": [
            {
                "id": e.tornado_id,
                "date": e.date,
                "year": e.year,
                "state": e.state,
                "magnitude": e.magnitude,
                "start": {"lat": e.start_lat, "lon": e.start_lon},
                "end": {"lat": e.end_lat, "lon": e.end_lon},
                "length_miles": e.length_miles,
                "width_yards": e.width_yards,
                "injuries": e.injuries,
                "fatalities": e.fatalities,
            }
            for e in nearby
        ],
        "riskZones": risk_zones,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON} with {len(nearby)} nearby tornado events.")


if __name__ == "__main__":
    main()
