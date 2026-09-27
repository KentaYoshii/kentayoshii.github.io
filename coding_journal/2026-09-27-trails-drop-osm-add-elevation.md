# 2026-09-27 — Trails: drop OpenStreetMap, add elevation gain

## Tasks
- Suggest long/popular trails for the 15 visited national parks; log the ones the user has walked.
- Remove the OpenStreetMap lookup from the trail log (user decision after a test run matched 1 of 4 trails and took >5 min of Overpass 504s).
- Add an optional hand-entered elevation gain field.

## Changes
- `scripts/build_trails.py`: offline-only parser. Removed `--fetch`, Overpass, cache, blaze/sac_scale handling. Added `parse_elevation()` (ft/feet/m → whole feet); fields after the name are classified by unit, not position. Summary gains `elevation_ft`, `elevation_text` (pre-formatted, Liquid has no thousands separator), `elevation_counted`; `resolved` removed.
- `docs/_data/trails_osm.json`: deleted.
- `docs/adventure/trails.markdown`: blaze bar and difficulty/surface tags removed; per-row "N ft gain"; tagline adds "N ft of climbing".
- `docs/assets/main.scss`: blaze and `.trail-tag` rules removed (light and dark); `.trail-gain` added; phone indent for the blaze removed.
- `.github/workflows/fetch.yml`: `trails` target removed.
- `README.md`, `docs/_logs/trails.md` header, `scripts/build_parks_map.py` docstring: OSM references removed, elevation format documented.
- `tests/`: OSM/cache/retry tests removed; elevation parsing and summary tests added.
- `docs/_logs/trails.md`: 12 hikes logged — Yellowstone ×7 (Oct 2025), Grand Teton ×3 (Sep 2025), Angels Landing (Apr 2025), Kīlauea Iki (Apr 2022). Months taken from the parks' photo EXIF dates. Elevations from the user except Angels Landing (NPS 1,488 ft); Fairy Falls distance from NPS (5.4 mi).

- `build_trails.py` second change: sort by date only (stable), so hikes within a month keep log order and stay grouped by park.

## Verification
- `python3 scripts/build.py`: only `trails.json` changed in `docs/_data`.
- `python3 -m pytest`: 365 passed.
- Jekyll not installed here; page not rendered locally. CI `site` job covers Liquid.

## TODOs
- All 15 visited parks logged: 55 hikes, 417.9 mi, 86,142 ft. Within a month, entries are ordered newest park first by photo dates.

## Learnings
- NPS trail stats live on `https://www.nps.gov/thingstodo/<park>-trail-<name>.htm`; links are listed on `/tripideas/day-hikes-in-the-<area>-area.htm`. Grand Teton's hiking page loads via JS. AllTrails returns 403 to scripts.
- OSM has no entries for loops/combined hikes, which is most long hikes; hand-entered data is more reliable.
