# Tornado History Tracker

Web-based ESRI map for visualizing tornado history near Huntsville, Alabama for the past 30 years. The map includes:

- Tornado events color-coded by EF/F category and marker size by magnitude.
- A risk-zone layer from least dangerous to most dangerous.
- Focus markers for Huntsville, Chapman Mountain, and Hampton Cove.
- Sidebar filters for magnitude and year range.

## Data Source

- NOAA/NWS Storm Prediction Center CSV:
  https://www.spc.noaa.gov/wcm/data/1950-2024_actual_tornadoes.csv

## Quick Start

1. Build processed dataset:

```bash
python3 scripts/build_dataset.py
```

2. Run a local static server from the project root:

```bash
python3 -m http.server 8088
```

3. Open:

`http://localhost:8088`

## Docker

Build and run with a single command (requires Docker):

```bash
# One-command start via Compose
docker compose -f docker/docker-compose.yml up -d

# Or build and run manually
docker build -f docker/Dockerfile -t tornado-history-tracker:latest .
docker run -d -p 8088:80 --name tornado-tracker tornado-history-tracker:latest
```

Open `http://localhost:8088` after the container starts.

To stop: `docker compose -f docker/docker-compose.yml down`

## Project Layout

- `index.html`: Main app shell.
- `src/app.js`: ArcGIS map logic, layers, and filtering.
- `src/styles.css`: UI styling.
- `scripts/build_dataset.py`: Fetches/filter/processes tornado data.
- `data/processed/huntsville_tornadoes_30y.json`: Generated map dataset.
- `docs/project_plan.md`: Phase plan and checklist.

## Method Notes

- Time range: latest 30 years available in source data.
- Spatial filter: events with start or end point within 35 miles of Huntsville center.
- Risk zones: weighted density on a regular grid based on distance and tornado magnitude.
- Classification: quantile buckets from least dangerous to most dangerous.

## Safety Note

This tool is for historical analysis and planning support only. It does not predict future tornado occurrence and should not replace official weather guidance.
