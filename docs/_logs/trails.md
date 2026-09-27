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

### September

- Highline Trail — Glacier National Park, MT — 17.13 mi — 3,556 ft
- Siyeh Pass and St. Mary Falls Loop — Glacier National Park, MT — 18.11 mi — 4,232 ft
- Grinnell Glacier — Glacier National Park, MT — 11.32 mi — 2,146 ft
- Ptarmigan Tunnel / Iceberg Lake — Glacier National Park, MT — 15.1 mi — 3,068 ft
- Avalanche Lake — Glacier National Park, MT — 6.4 mi — 801 ft
- Swiftcurrent Pass — Glacier National Park, MT — 15.78 mi — 2,972 ft
- Numa Lookout — Glacier National Park, MT — 11.58 mi — 3,012 ft
- Mount Ida — Rocky Mountain National Park, CO — 9.6 mi — 2,400 ft
- Sprague, Nymph, Dream, Emerald and Haiyaha Lakes to Sky Pond — Rocky Mountain National Park, CO — 20.3 mi — 3,278 ft
- Chasm Lake — Rocky Mountain National Park, CO — 8.5 mi — 2,542 ft
- Ouzel Falls — Rocky Mountain National Park, CO — 5.6 mi — 980 ft

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

- Alkali Flat Trail — White Sands National Park, NM — 4.3 mi — 49 ft
- Smith Spring and Manzanita Spring Loop — Guadalupe Mountains National Park, TX — 2.53 mi — 387 ft
- McKittrick Canyon to The Notch — Guadalupe Mountains National Park, TX — 18 mi — 3,200 ft
- Hunter Peak via Bear Canyon — Guadalupe Mountains National Park, TX — 9.09 mi — 2,703 ft
- Guadalupe Peak — Guadalupe Mountains National Park, TX — 9.54 mi — 3,163 ft
- Devil's Hall — Guadalupe Mountains National Park, TX — 5.5 mi — 700 ft
- Natural Entrance and Big Room — Carlsbad Caverns National Park, NM — 3.75 mi — 750 ft
- Desert Nature Trail — Carlsbad Caverns National Park, NM — 1.2 mi — 72 ft
- Emory Peak via South Rim and Boot Springs Trails — Big Bend National Park, TX — 14.6 mi — 3,166 ft
- Upper Burro Mesa Pouroff — Big Bend National Park, TX — 3.6 mi — 439 ft
- Lower Burro Mesa Pouroff — Big Bend National Park, TX — 1 mi — 157 ft
- Santa Elena Canyon Trail — Big Bend National Park, TX — 1.7 mi — 242 ft
- The Window Trail — Big Bend National Park, TX — 5.5 mi — 958 ft
- Lost Mine Trail — Big Bend National Park, TX — 4.8 mi — 1,145 ft
- Ernst Ridge Trail — Big Bend National Park, TX — 6 mi — 954 ft
- Boquillas Canyon Trail — Big Bend National Park, TX — 1.5 mi — 150 ft
- Dog Canyon and Devil's Den — Big Bend National Park, TX — 10 mi — 689 ft

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

## 2024

### January

- Tongariro Alpine Crossing — Tongariro National Park, New Zealand — 12.6 mi — 2,798 ft
- Routeburn Track — Fiordland National Park, New Zealand — 4.6 mi — 1,003 ft
- Hooker Valley Track — Aoraki/Mount Cook National Park, New Zealand — 6.9 mi — 708 ft
- Mueller Hut Route — Aoraki/Mount Cook National Park, New Zealand — 7.36 mi — 3,540 ft
- Mount John Walkway — Lake Tekapo, New Zealand — 5.2 mi — 1,315 ft

## 2022

### April

- Kīlauea Iki Trail — Hawaiʻi Volcanoes National Park, HI — 3.3 mi — 760 ft
