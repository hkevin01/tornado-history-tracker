/* OpenLayers implementation — global `ol` object from CDN UMD build */

// Dataset centre (Huntsville) and the radius we clip rendered paths to.
// Tornadoes that started in Mississippi still hit the Huntsville area — we
// just don't draw the 100+ miles of track that are outside our study region.
const CENTER_LAT = 34.7304;
const CENTER_LON = -86.5861;
const PATH_CLIP_MILES = 38; // slightly larger than the 35-mile dataset radius

function colorForMagnitude(mag) {
  if (mag >= 5) return "#8e44ad";
  if (mag >= 4) return "#e74c3c";
  if (mag >= 3) return "#e67e22";
  if (mag >= 2) return "#f39c12";
  if (mag >= 1) return "#f4d03f";
  return "#8bc34a";
}

// scoreNorm is a 0–1 log-scaled value stored on each zone cell.
// Using it for alpha instead of fixed opacity creates smooth fuzzy gradients
// at zone boundaries rather than hard-edged squares.
function colorForRisk(level, scoreNorm) {
  const BASES = {
    "Most Dangerous":  [169, 36,  30],
    "High":            [226, 96,  52],
    "Moderate":        [236, 162, 67],
    "Low":             [102, 178, 82],
    "Least Dangerous": [44,  148, 86],
  };
  const [r, g, b] = BASES[level] || BASES["Least Dangerous"];
  const alpha = (0.07 + (scoreNorm || 0) * 0.70).toFixed(2);
  return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
}

function tornadoFeature(event) {
  const f = new ol.Feature({
    geometry: new ol.geom.Point(
      ol.proj.fromLonLat([event.start.lon, event.start.lat])
    ),
  });
  const radius = Math.min(10, 3 + Math.max(0, event.magnitude) * 1);
  f.setStyle(
    new ol.style.Style({
      image: new ol.style.Circle({
        radius,
        fill: new ol.style.Fill({ color: colorForMagnitude(event.magnitude) }),
        stroke: new ol.style.Stroke({ color: "#1f1f1f", width: 0.7 }),
      }),
      zIndex: 2,
    })
  );
  f.set(
    "_popup",
    "<b>Tornado " + event.year + " (EF/F " + event.magnitude + ")</b><br/>" +
    "<b>Date:</b> " + event.date + "<br/>" +
    "<b>Length:</b> " + event.length_miles + " mi<br/>" +
    "<b>Width:</b> " + event.width_yards + " yd<br/>" +
    "<b>Injuries:</b> " + event.injuries + "<br/>" +
    "<b>Fatalities:</b> " + event.fatalities
  );
  return f;
}

/**
 * Clip a lat/lon point radially toward the Huntsville centre so that
 * out-of-area track endpoints don't produce 100+ mile lines on the map.
 * Points already inside the radius are returned unchanged.
 */
function clipToArea(lat, lon) {
  const d = haversineMiles(CENTER_LAT, CENTER_LON, lat, lon);
  if (d <= PATH_CLIP_MILES) return [lat, lon];
  const frac = PATH_CLIP_MILES / d;
  return [
    CENTER_LAT + (lat - CENTER_LAT) * frac,
    CENTER_LON + (lon - CENTER_LON) * frac,
  ];
}

/** Compass bearing in radians (clockwise from north) between two WGS-84 points. */
function bearingRad(lat1, lon1, lat2, lon2) {
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const lat1R = lat1 * Math.PI / 180;
  const lat2R = lat2 * Math.PI / 180;
  const y = Math.sin(dLon) * Math.cos(lat2R);
  const x = Math.cos(lat1R) * Math.sin(lat2R)
           - Math.sin(lat1R) * Math.cos(lat2R) * Math.cos(dLon);
  return Math.atan2(y, x);
}

/**
 * Build 1-2 OL features for a tornado track:
 *   [0] the line (clipped to the study area)
 *   [1] a direction-arrow triangle at the midpoint of the clipped line
 * Returns an empty array when start === end after clipping.
 */
function tornadoPathFeatures(event) {
  const [sLat, sLon] = clipToArea(event.start.lat, event.start.lon);
  const [eLat, eLon] = clipToArea(event.end.lat, event.end.lon);

  // Skip if clipping collapsed the track to a single point
  if (Math.abs(sLat - eLat) < 1e-5 && Math.abs(sLon - eLon) < 1e-5) return [];

  const color = colorForMagnitude(event.magnitude);
  const lineWidth = Math.max(1.5, Math.min(6, 1.5 + event.magnitude * 0.9));
  const popupHtml =
    "<b>Track " + event.year + " (EF/F " + event.magnitude + ")</b><br/>" +
    "<b>Date:</b> " + event.date + "<br/>" +
    "<b>Reported length:</b> " + event.length_miles + " mi<br/>" +
    "<b>Width:</b> " + event.width_yards + " yd<br/>" +
    "<small><i>Path clipped to study area — full track may extend further.</i></small>";

  // Line feature
  const line = new ol.Feature({
    geometry: new ol.geom.LineString([
      ol.proj.fromLonLat([sLon, sLat]),
      ol.proj.fromLonLat([eLon, eLat]),
    ]),
  });
  line.setStyle(new ol.style.Style({
    stroke: new ol.style.Stroke({ color, width: lineWidth }),
    zIndex: 1,
  }));
  line.set("_popup", popupHtml);

  // Direction-arrow triangle at the clipped midpoint
  const midLat = (sLat + eLat) / 2;
  const midLon = (sLon + eLon) / 2;
  const br = bearingRad(sLat, sLon, eLat, eLon);
  const arrow = new ol.Feature({
    geometry: new ol.geom.Point(ol.proj.fromLonLat([midLon, midLat])),
  });
  // OL RegularShape with points:3, angle:0 draws a triangle pointing UP (north).
  // Rotating by `br` aligns it with the track direction.
  const arrowRadius = Math.max(5, Math.min(9, 4 + event.magnitude));
  arrow.setStyle(new ol.style.Style({
    image: new ol.style.RegularShape({
      points: 3,
      radius: arrowRadius,
      angle: 0,
      rotation: br,
      fill: new ol.style.Fill({ color }),
      stroke: new ol.style.Stroke({ color: "rgba(0,0,0,0.5)", width: 0.8 }),
    }),
    zIndex: 1,
  }));
  arrow.set("_popup", popupHtml);

  return [line, arrow];
}

function riskFeature(zone) {
  const [xmin, ymin, xmax, ymax] = zone.bbox;
  const ring = [
    [xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax], [xmin, ymin],
  ].map(function(c) { return ol.proj.fromLonLat(c); });
  const f = new ol.Feature({
    geometry: new ol.geom.Polygon([ring]),
  });
  f.setStyle(
    new ol.style.Style({
      fill: new ol.style.Fill({ color: colorForRisk(zone.level, zone.scoreNorm) }),
      stroke: new ol.style.Stroke({ color: "rgba(40,40,40,0.05)", width: 0.1 }),
      zIndex: 0,
    })
  );
  const region = zone.region || {};
  f.set(
    "_popup",
    "<b>" + (region.name || "Risk Zone") + "</b><br/>" +
    "<b>Risk level:</b> " + zone.level + "<br/>" +
    "<b>Historical score:</b> " + zone.score + "<br/>" +
    (region.why
      ? "<br/><span style='font-size:0.78rem;color:#555;line-height:1.4'>" + region.why + "</span>"
      : "")
  );
  return f;
}

function haversineMiles(lat1, lon1, lat2, lon2) {
  const R = 3958.8;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

const RISK_RANK = {
  "Least Dangerous": 1,
  "Low": 2,
  "Moderate": 3,
  "High": 4,
  "Most Dangerous": 5,
};

function candidateMetrics(name, lat, lon, events, riskZones, radiusMiles) {
  radiusMiles = radiusMiles === undefined ? 5 : radiusMiles;
  const near = events.filter(function(e) {
    return (
      haversineMiles(lat, lon, e.start.lat, e.start.lon) <= radiusMiles ||
      haversineMiles(lat, lon, e.end.lat, e.end.lon) <= radiusMiles
    );
  });
  const ef2plus = near.filter(function(e) { return e.magnitude >= 2; }).length;
  const injuries = near.reduce(function(s, e) { return s + (e.injuries || 0); }, 0);
  const fatalities = near.reduce(function(s, e) { return s + (e.fatalities || 0); }, 0);

  const containing = riskZones.filter(function(z) {
    const b = z.bbox;
    return lon >= b[0] && lon <= b[2] && lat >= b[1] && lat <= b[3];
  });

  let riskLevel = "Unknown";
  let riskScore = 0;
  if (containing.length > 0) {
    const cell = containing.slice().sort(function(a, b) { return a.score - b.score; })[0];
    riskLevel = cell.level;
    riskScore = cell.score;
  }

  return { name, total: near.length, ef2plus, injuries, fatalities, riskLevel, riskScore };
}

function renderCandidateComparison(filteredEvents, riskZones) {
  const candidates = [
    { name: "Chapman Mountain", lat: 34.7679, lon: -86.5294 },
    { name: "Hampton Cove",     lat: 34.6353, lon: -86.4867 },
  ];

  const metrics = candidates.map(function(c) {
    return candidateMetrics(c.name, c.lat, c.lon, filteredEvents, riskZones);
  });

  const ranked = metrics.slice().sort(function(a, b) {
    const rDiff = (RISK_RANK[a.riskLevel] || 3) - (RISK_RANK[b.riskLevel] || 3);
    if (rDiff !== 0) return rDiff;
    const sDiff = a.riskScore - b.riskScore;
    if (Math.abs(sDiff) > 0.01) return sDiff;
    return a.total - b.total;
  });

  const el = document.getElementById("candidateTable");
  if (!el) return;

  let html = '<table class="cmp-table"><thead><tr><th>Metric</th>';
  ranked.forEach(function(m, i) {
    const badge =
      i === 0
        ? ' <span class="rank-winner">Safer #1</span>'
        : ' <span class="rank-second">#2</span>';
    html += "<th>" + m.name + badge + "</th>";
  });
  html += "</tr></thead><tbody>";

  const rows = [
    ["Nearby events (5 mi)", function(m) { return m.total; }],
    ["EF2+ events",          function(m) { return m.ef2plus; }],
    ["Injuries nearby",      function(m) { return m.injuries; }],
    ["Fatalities nearby",    function(m) { return m.fatalities; }],
    ["Risk level",           function(m) { return m.riskLevel; }],
    ["Risk score",           function(m) { return m.riskScore.toFixed(2); }],
  ];

  rows.forEach(function(row) {
    html += "<tr><td>" + row[0] + "</td>";
    ranked.forEach(function(m) {
      html += "<td>" + row[1](m) + "</td>";
    });
    html += "</tr>";
  });

  html += "</tbody></table>";
  el.innerHTML = html;
}

function renderStats(dataset, filteredEvents, filteredZones) {
  const stats = document.getElementById("stats");
  const chapman = filteredEvents.filter(function(e) {
    return Math.abs(e.start.lat - 34.7679) < 0.12 && Math.abs(e.start.lon + 86.5294) < 0.12;
  }).length;
  const hampton = filteredEvents.filter(function(e) {
    return Math.abs(e.start.lat - 34.6353) < 0.12 && Math.abs(e.start.lon + 86.4867) < 0.12;
  }).length;
  const least = filteredZones
    .filter(function(z) { return z.level === "Least Dangerous"; })
    .slice(0, 6).length;

  stats.innerHTML =
    "<b>Events shown:</b> " + filteredEvents.length + "<br/>" +
    "<b>Source years:</b> " + dataset.meta.year_range[0] + "-" + dataset.meta.year_range[1] + "<br/>" +
    "<b>Chapman Mountain nearby events:</b> " + chapman + "<br/>" +
    "<b>Hampton Cove nearby events:</b> " + hampton + "<br/>" +
    "<b>Least-dangerous cells in view:</b> " + least + "<br/>" +
    "<small>Use this as a historical guide, not a guarantee of future safety.</small>";
}

// ── Main ──────────────────────────────────────────────────────────────────────
(async function () {
  let dataset;
  try {
    const response = await fetch("./data/processed/huntsville_tornadoes_30y.json");
    dataset = await response.json();
  } catch (err) {
    document.getElementById("stats").textContent =
      "Unable to load processed dataset. Run scripts/build_dataset.py first.";
    console.error("Dataset load error:", err);
    return;
  }

  // Vector sources
  const riskSource    = new ol.source.Vector();
  const pathSource    = new ol.source.Vector();
  const tornadoSource = new ol.source.Vector();
  const placesSource  = new ol.source.Vector();

  // Vector layers (risk zones at bottom → paths → points → places on top)
  const riskLayer    = new ol.layer.Vector({ source: riskSource,    zIndex: 0 });
  const pathLayer    = new ol.layer.Vector({ source: pathSource,    zIndex: 1 });
  const tornadoLayer = new ol.layer.Vector({ source: tornadoSource, zIndex: 2 });
  const placesLayer  = new ol.layer.Vector({ source: placesSource,  zIndex: 3 });

  // Map
  const map = new ol.Map({
    target: "viewDiv",
    layers: [
      new ol.layer.Tile({ source: new ol.source.OSM() }),
      riskLayer,
      pathLayer,
      tornadoLayer,
      placesLayer,
    ],
    view: new ol.View({
      center: ol.proj.fromLonLat([
        dataset.meta.center.lon,
        dataset.meta.center.lat,
      ]),
      zoom: 9,
    }),
  });

  // ── Popup overlay ───────────────────────────────────────────────────────────
  const popupEl      = document.getElementById("popup");
  const popupContent = document.getElementById("popup-content");
  const popupCloser  = document.getElementById("popup-closer");

  const popup = new ol.Overlay({
    element: popupEl,
    positioning: "bottom-center",
    stopEvent: false,
    offset: [0, -8],
  });
  map.addOverlay(popup);

  popupCloser.addEventListener("click", function (e) {
    e.preventDefault();
    popup.setPosition(undefined);
    popupCloser.blur();
  });

  map.on("click", function (evt) {
    const feature = map.forEachFeatureAtPixel(evt.pixel, function (f) {
      return f;
    });
    if (feature && feature.get("_popup")) {
      popupContent.innerHTML = feature.get("_popup");
      popup.setPosition(evt.coordinate);
    } else {
      popup.setPosition(undefined);
    }
  });

  // Change cursor on hover
  map.on("pointermove", function (evt) {
    const hit = map.hasFeatureAtPixel(evt.pixel);
    map.getTargetElement().style.cursor = hit ? "pointer" : "";
  });

  // ── Reference places ────────────────────────────────────────────────────────
  dataset.places.forEach(function (place) {
    const f = new ol.Feature({
      geometry: new ol.geom.Point(ol.proj.fromLonLat([place.lon, place.lat])),
    });
    f.setStyle(
      new ol.style.Style({
        image: new ol.style.RegularShape({
          points: 4,
          radius: 7,
          angle: Math.PI / 4,
          fill: new ol.style.Fill({ color: "#12466b" }),
          stroke: new ol.style.Stroke({ color: "#fff", width: 0.9 }),
        }),
        zIndex: 10,
      })
    );
    f.set("_popup", "<b>" + place.name + "</b>");
    placesSource.addFeature(f);
  });

  // ── Year-range defaults ─────────────────────────────────────────────────────
  const minYear = dataset.meta.year_range[0];
  const maxYear = dataset.meta.year_range[1];
  const yearStartEl = document.getElementById("yearStart");
  const yearEndEl   = document.getElementById("yearEnd");
  yearStartEl.value = String(minYear);  // default: show all 30 years
  yearEndEl.value   = String(maxYear);

  // ── Filters ─────────────────────────────────────────────────────────────────
  function applyFilters() {
    const minMag    = Number(document.getElementById("minMag").value);
    const startYear = Number(yearStartEl.value);
    const endYear   = Number(yearEndEl.value);
    const showRisk  = document.getElementById("toggleRisk").checked;
    const showPaths = document.getElementById("togglePaths").checked;

    popup.setPosition(undefined);

    const filteredEvents = dataset.tornadoes.filter(function (e) {
      return e.magnitude >= minMag && e.year >= startYear && e.year <= endYear;
    });

    // Paths
    pathSource.clear();
    pathLayer.setVisible(showPaths);
    if (showPaths) {
      filteredEvents.forEach(function (event) {
        tornadoPathFeatures(event).forEach(function (f) {
          pathSource.addFeature(f);
        });
      });
    }

    // Points
    tornadoSource.clear();
    filteredEvents.forEach(function (event) {
      tornadoSource.addFeature(tornadoFeature(event));
    });

    // Risk zones
    riskSource.clear();
    riskLayer.setVisible(showRisk);
    const filteredZones = dataset.riskZones;
    filteredZones.forEach(function (zone) {
      riskSource.addFeature(riskFeature(zone));
    });

    renderStats(dataset, filteredEvents, filteredZones);
    renderCandidateComparison(filteredEvents, filteredZones);
  }

  document.getElementById("applyFilters").addEventListener("click", applyFilters);
  applyFilters();
})();
