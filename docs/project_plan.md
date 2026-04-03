# Tornado History Tracker Project Plan

## Phase 1 - Foundation and Data Pipeline
- [x] Create project structure and documentation baseline.
- [x] Implement dataset ingestion from SPC CSV.
- [x] Filter tornadoes to the past 30 years near Huntsville, AL.
- [x] Generate risk-zone grid with least-dangerous to most-dangerous scoring.

Phase 1 Gate: PASS
- [x] Tasks complete
- [x] Data build succeeds
- [x] Error handling added for data parsing and IO

## Phase 2 - ESRI Web Map Experience
- [x] Build web map using ArcGIS JavaScript API.
- [x] Plot tornado points color-coded by EF/F category.
- [x] Add risk-zone layer with ordered danger colors.
- [x] Add target-area markers for Chapman Mountain and Hampton Cove.

Phase 2 Gate: PASS
- [x] Tasks complete
- [x] Map layers load from generated JSON
- [x] Controls and popups wired

## Phase 3 - Analysis UX and Delivery
- [x] Add filtering controls (year range, minimum magnitude).
- [x] Add statistics panel and quick findings.
- [x] Validate happy path, edge case, and error conditions.
- [x] Finalize README, CHANGELOG, and gate checklist.

Phase 3 Gate: PASS
- [x] Tasks complete
- [x] Unit tests pass
- [x] Local run smoke test passes
- [x] Docs and changelog updated

## Phase 4 - Location Search and Candidate Comparison
- [x] Add ESRI Search widget (ZIP/address geocoding) to the MapView.
- [x] Add `haversineMiles` distance helper to frontend JS.
- [x] Add `candidateMetrics()` function — computes 5-mile historical exposure for any lat/lon.
- [x] Add `renderCandidateComparison()` — ranked table for Chapman Mountain vs Hampton Cove.
- [x] Wire comparison table to filter apply so it updates dynamically.
- [x] Style candidate table with winner/runner-up badges.

Phase 4 Gate: PASS
- [x] Tasks complete
- [x] Search widget loads in MapView
- [x] Comparison table renders on page load and filter changes
- [x] Docs and changelog updated

## Phase 5 - Docker Containerisation
- [x] Create `docker/Dockerfile` using nginx:alpine (static file server).
- [x] Create `docker/nginx.conf` with correct MIME types, cache headers, and no-store for dataset.
- [x] Create `docker/docker-compose.yml` mapping host port 8088 → container port 80.
- [x] Create `.dockerignore` to exclude raw CSV, scripts, tests, and docs (keeps image ≤100 MB).
- [x] Build image and verify HTTP 200 on index.html.
- [x] Verify dataset endpoint serves correct JSON inside container.

Phase 5 Gate: PASS
- [x] Image builds successfully (`tornado-history-tracker:latest`, ~93 MB)
- [x] Container starts and passes health check
- [x] HTTP 200 on `/index.html` and `/data/processed/huntsville_tornadoes_30y.json`

## Implementation Notes
- Data source: NOAA/SPC historical tornado CSV.
- Mapping engine: ArcGIS JavaScript API (ESRI web map).
- Risk model: weighted tornado density and intensity on a regular grid.
