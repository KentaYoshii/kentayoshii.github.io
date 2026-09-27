# Trails

Source of truth for the trail log on the Adventure page.
`scripts/build_trails.py` reads this into `docs/_data/trails.json`.

Format, one hike per line under a `## <year>` and an optional `### <month>`:

```
- <trail name> — <where> — <distance> — <elevation gain>
```

The separator is an em dash (`—`), or `--` if that is easier to type. Do not
use a plain ` - `: real trail names contain it ("Suffern - Bear Mountain
Trail"), and the parser would split in the wrong place.

Only the name is required. Distance accepts `6.2 mi`, `10 km` or `5 miles`;
elevation gain accepts `4,350 ft` or `1,300 m`. Fields after the name are
recognised by their units, so any of them can be left out.

After editing, regenerate and commit:

```sh
python3 scripts/build.py
```

## 2026

## 2025

### October

- Fairy Falls Trail — Yellowstone National Park, WY — 5.4 mi — 173 ft
- Upper Geyser Basin and Old Faithful Observation Point Loop — Yellowstone National Park, WY
- Mammoth Hot Springs Trail — Yellowstone National Park, MT
- Beaver Ponds Loop Trail — Yellowstone National Park, MT — 5.7 mi — 757 ft
- Seven Mile Hole — Yellowstone National Park, WY — 10.3 mi — 2,083 ft
- Dunraven Pass to Mount Washburn — Yellowstone National Park, WY — 7.1 mi — 1,400 ft
- Artist Point via South Rim Trail — Yellowstone National Park, WY

### September

- Paintbrush–Cascade Canyon Loop — Grand Teton National Park, WY — 19 mi — 4,133 ft
- Surprise and Amphitheater Lakes — Grand Teton National Park, WY — 10 mi — 3,000 ft
- Taggart and Bradley Lakes Loop — Grand Teton National Park, WY — 5.9 mi — 767 ft

### April

- Angels Landing — Zion National Park, UT — 5.4 mi — 1,488 ft

## 2022

### April

- Kīlauea Iki Trail — Hawaiʻi Volcanoes National Park, HI — 3.3 mi — 760 ft
