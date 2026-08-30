# Travel

Source of truth for the Travel page. `scripts/build_travel.py` reads this
into `docs/_data/travel.json`.

A `##` heading is a category (currently just "National Parks"; a "## Cities"
category can be added later without restructuring this file). A `###`
heading within a category is the year visited. Park names are matched
loosely against `scripts/national_parks.py`'s reference list — see that
file's ALIASES for the handful that need an explicit mapping.

## National Parks

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
