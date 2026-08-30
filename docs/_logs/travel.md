# Travel

Source of truth for the Travel page. `scripts/build_travel.py` reads this
into `docs/_data/travel.json`.

A `##` heading is a category — currently just "US National Parks"; a
"## Countries" category (or similar) can be registered later in
`scripts/build_travel.py`'s CHECKLISTS without restructuring this file. A
`###` heading within a category is the year visited. Names are matched
loosely against the category's reference list — see `national_parks.py`'s
ALIASES for the handful that need an explicit mapping.

## US National Parks

### 2025
- Zion
- Grand Canyon
- Yosemite
- Grand Teton
- Yellowstone
- Big Bend
- White Sands
- Guadalupe
- Carlsbad Caverns

### 2026
- Haleakala
- Hawaiian Volcanoes
- Rocky Mountains
- Olympic
- Mount Rainier
