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

### July

- Hoh River Trail — Olympic National Park, WA — 11.25 mi — 400 ft
- Hall of Mosses Trail — Olympic National Park, WA — 1.4 mi — 82 ft
- Mount Storm King / Marymere Falls — Olympic National Park, WA — 5.54 mi — 2,343 ft
- Sol Duc Falls Trail — Olympic National Park, WA — 1.8 mi — 262 ft
- Hurricane Hill — Olympic National Park, WA — 3.2 mi — 903 ft
- Cape Flattery Trail — Olympic National Park, WA — 1.3 mi — 232 ft
- Quinault Loop — Olympic National Park, WA — 4.5 mi — 394 ft
- Second Beach — Olympic National Park, WA — 2.2 mi — 291 ft
- Maple Glade Nature Trail — Olympic National Park, WA — 1 mi — 20 ft
- Skyline Loop / Reflection Lake / Pinnacle Peak — Mount Rainier National Park, WA — 12.4 mi — 3,661 ft
- Bench and Snow Lakes Trail — Mount Rainier National Park, WA — 2.3 mi — 470 ft
- Mount Fremont Lookout and Burroughs Mountain Loop — Mount Rainier National Park, WA — 10.92 mi — 2,740 ft

### April

- Sliding Sands Trail — Haleakalā National Park, HI — 18.2 mi — 4,140 ft

## 2025

### December

- Smith Spring and Manzanita Spring Loop — Guadalupe Mountains National Park, TX — 2.53 mi — 387 ft
- McKittrick Canyon to The Notch — Guadalupe Mountains National Park, TX — 18 mi — 3,200 ft
- Hunter Peak via Bear Canyon — Guadalupe Mountains National Park, TX — 9.09 mi — 2,703 ft
- Guadalupe Peak — Guadalupe Mountains National Park, TX — 9.54 mi — 3,163 ft
- Devil's Hall — Guadalupe Mountains National Park, TX — 5.5 mi — 700 ft
- Natural Entrance and Big Room — Carlsbad Caverns National Park, NM — 3.75 mi — 750 ft
- Desert Nature Trail — Carlsbad Caverns National Park, NM — 1.2 mi — 72 ft
- Alkali Flat Trail — White Sands National Park, NM — 4.3 mi — 49 ft

### October

- Fairy Falls Trail — Yellowstone National Park, WY — 5.4 mi — 173 ft
- Upper Geyser Basin and Old Faithful Observation Point Loop — Yellowstone National Park, WY — 4.9 mi — 357 ft
- Mammoth Hot Springs Trail — Yellowstone National Park, MT — 2.2 mi — 321 ft
- Beaver Ponds Loop Trail — Yellowstone National Park, MT — 5.7 mi — 757 ft
- Seven Mile Hole — Yellowstone National Park, WY — 10.3 mi — 2,083 ft
- Dunraven Pass to Mount Washburn — Yellowstone National Park, WY — 7.1 mi — 1,400 ft
- Artist Point via South Rim Trail — Yellowstone National Park, WY — 2.8 mi — 300 ft

### September

- Paintbrush–Cascade Canyon Loop — Grand Teton National Park, WY — 19 mi — 4,133 ft
- Surprise and Amphitheater Lakes — Grand Teton National Park, WY — 10 mi — 3,000 ft
- Taggart and Bradley Lakes Loop — Grand Teton National Park, WY — 5.9 mi — 767 ft

### May

- Yosemite Point — Yosemite National Park, CA — 8.7 mi — 3,720 ft

### April

- Bright Angel Trail to Havasupai Gardens — Grand Canyon National Park, AZ — 9.2 mi — 3,034 ft
- Angels Landing — Zion National Park, UT — 5.4 mi — 1,488 ft

## 2022

### April

- Kīlauea Iki Trail — Hawaiʻi Volcanoes National Park, HI — 3.3 mi — 760 ft
