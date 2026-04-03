# Changelog

## 0.3.0 - 2026-04-02

- Added `docker/Dockerfile` using nginx:alpine to containerise the static web app.
- Added `docker/nginx.conf` with correct MIME types and cache-control headers.
- Added `docker/docker-compose.yml` for one-command startup on port 8088.
- Added `.dockerignore` to exclude raw data, scripts, tests, and docs (image ~93 MB).

## 0.2.0 - 2026-04-02

- Added ESRI Search widget to MapView for ZIP code and address geocoding.
- Added candidate zone comparison table: Chapman Mountain vs Hampton Cove ranked by historical tornado exposure.
- Candidate metrics include total nearby events, EF2+ count, injuries, fatalities, risk level, and risk score within a 5-mile radius.
- Comparison table updates dynamically when filters are applied.

## 0.1.0 - 2026-04-02

- Created Tornado History Tracker project scaffold.
- Added SPC data build script for Huntsville-area 30-year filtering.
- Added risk-zone grid generation (least to most dangerous).
- Implemented ESRI web map with tornado point and risk-zone layers.
- Added filtering UI (magnitude and year range) and summary statistics panel.
