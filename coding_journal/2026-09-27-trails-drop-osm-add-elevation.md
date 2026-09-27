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
- Park grouping (follow-up): `build_trails.py` matches each hike to its travel.json park (`park_of`), groups consecutive same-month same-park hikes (`group`, `first_of_park` flags the anchor), and writes per-park totals (`by_park`). Output is `groups` / `parks` / `summary`; the flat `trails` list was dropped as a duplicate. `trails.markdown` renders park headings in the park's photo colour, linking to `/adventure/parks/`; rows show name, distance, gain only. `parks.markdown` shows "N hikes, X mi" in each photo section head and "N hikes" on checklist tiles, linking to `/adventure/trails/#park-<slug>`. Hub card adds the climbing total.
- Follow-ups: unmatched-park warning (`unmatched_parks`); gain bar (`gain_pct`) and records line (`records`); "miles hiked" pill on the home page; photo-to-hike links — `trail:` on 67 gallery.yml entries (matched by GPS/date/caption, user confirmed), `attach_photos` puts file names on each hike, trails page shows a 📷 toggle per hike opening a lazy photo set that reuses the parks-page lightbox (`[data-photo-set]`; `applyTagFilter` skipped without a filter bar so sets stay collapsed), lightbox meta adds the trail. Window caption corrected from "pour-off".
- NZ hikes (Jan 2024): 5 logged with the user's distances and gains (Routeburn was a 4.6 mi section, not the traverse); Tongariro distance is DOC's 20.2 km as 12.6 mi. `unmatched_parks` now skips places whose region is not a two-letter US state code.
- 43 new photos (user commit 14ad51e): gallery.yml entries with captions from contact sheets and trails from GPS/time (Seven Mile Hole for IMG_2361 is inferred: north-rim position on the afternoon after Washburn). 2025 sections reordered by photo count per the file's rule. 96 photos on 41 hikes. Derivatives built.
- `combine_colours` now takes the saturation-weighted medoid hue (an actual photo's hue) instead of a circular mean, which had turned blue-sky + red-rock parks purple. Grand Canyon #503254 → #323954, Haleakalā red → brown; others near-unchanged.

## Verification
- `python3 scripts/build.py`: only `trails.json` changed in `docs/_data`.
- `python3 -m pytest`: 422 passed.
- Jekyll not installed here; page not rendered locally. CI `site` job covers Liquid.

## TODOs
- Unassigned photos (no matching logged hike): Hidden Lake, Lake McDonald, Big Bend "window in the rock" and Rio Grande, Olympic boardwalk, Haleakalā set, Zion overlook, Grand Canyon rim, Yellowstone Lake, Yosemite sequoias.
- All 15 visited parks logged: 55 hikes, 417.9 mi, 86,142 ft. Within a month, entries are ordered newest park first by photo dates.

## Learnings
- NPS trail stats live on `https://www.nps.gov/thingstodo/<park>-trail-<name>.htm`; links are listed on `/tripideas/day-hikes-in-the-<area>-area.htm`. Grand Teton's hiking page loads via JS. AllTrails returns 403 to scripts.
- OSM has no entries for loops/combined hikes, which is most long hikes; hand-entered data is more reliable.
