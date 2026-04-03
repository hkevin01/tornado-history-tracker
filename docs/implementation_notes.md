# Implementation Notes

## Data Pipeline (`scripts/build_dataset.py`)
- Downloads SPC historical tornado CSV.
- Filters to the latest 30 years near Huntsville (35-mile radius).
- Computes weighted risk grid and quantile risk levels.
- Emits `data/processed/huntsville_tornadoes_30y.json` for frontend use.

## Web Map (`index.html`, `src/app.js`)
- Uses ArcGIS JavaScript API as the ESRI map base.
- Renders tornado markers with EF/F category color and size encoding.
- Renders risk-zone polygons from least dangerous to most dangerous.
- Adds controls for minimum magnitude and year range filtering.

## UI/Styling (`src/styles.css`)
- Responsive map + control panel layout.
- Color legend aligned with tornado category symbols.
- Statistics panel to summarize filtered historical exposure.

## Testing (`tests/test_build_dataset.py`)
- Covers helper happy-path behavior (distance and risk-zone generation).
- Covers edge case behavior (near vs far event inclusion).
- Covers error handling behavior (invalid numeric parsing fallback).
