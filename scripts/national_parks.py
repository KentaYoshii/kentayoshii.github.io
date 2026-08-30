"""Reference list of every US National Park — the NPS's "National Park"
designation specifically, not monuments, preserves, seashores, or historic
sites. This is not a log: unlike _logs/travel.md, it does not represent
anything visited, it is the fixed universe a visit gets checked off against.

63 parks, last verified against nps.gov in August 2026. New ones are
designated occasionally (most recently New River Gorge, redesignated from a
National River in December 2020) — if the checklist ever looks short a
park, this is the first place to check against the current NPS list.

No network, no I/O: a plain Python list, imported by build_travel.py.
"""

NATIONAL_PARKS = [
    ('Acadia', 'Maine'),
    ('American Samoa', 'American Samoa'),
    ('Arches', 'Utah'),
    ('Badlands', 'South Dakota'),
    ('Big Bend', 'Texas'),
    ('Biscayne', 'Florida'),
    ('Black Canyon of the Gunnison', 'Colorado'),
    ('Bryce Canyon', 'Utah'),
    ('Canyonlands', 'Utah'),
    ('Capitol Reef', 'Utah'),
    ('Carlsbad Caverns', 'New Mexico'),
    ('Channel Islands', 'California'),
    ('Congaree', 'South Carolina'),
    ('Crater Lake', 'Oregon'),
    ('Cuyahoga Valley', 'Ohio'),
    ('Death Valley', 'California / Nevada'),
    ('Denali', 'Alaska'),
    ('Dry Tortugas', 'Florida'),
    ('Everglades', 'Florida'),
    ('Gates of the Arctic', 'Alaska'),
    ('Gateway Arch', 'Missouri'),
    ('Glacier', 'Montana'),
    ('Glacier Bay', 'Alaska'),
    ('Grand Canyon', 'Arizona'),
    ('Grand Teton', 'Wyoming'),
    ('Great Basin', 'Nevada'),
    ('Great Sand Dunes', 'Colorado'),
    ('Great Smoky Mountains', 'Tennessee / North Carolina'),
    ('Guadalupe Mountains', 'Texas'),
    ('Haleakalā', 'Hawaii'),
    ('Hawaiʻi Volcanoes', 'Hawaii'),
    ('Hot Springs', 'Arkansas'),
    ('Indiana Dunes', 'Indiana'),
    ('Isle Royale', 'Michigan'),
    ('Joshua Tree', 'California'),
    ('Katmai', 'Alaska'),
    ('Kenai Fjords', 'Alaska'),
    ('Kings Canyon', 'California'),
    ('Kobuk Valley', 'Alaska'),
    ('Lake Clark', 'Alaska'),
    ('Lassen Volcanic', 'California'),
    ('Mammoth Cave', 'Kentucky'),
    ('Mesa Verde', 'Colorado'),
    ('Mount Rainier', 'Washington'),
    ('New River Gorge', 'West Virginia'),
    ('North Cascades', 'Washington'),
    ('Olympic', 'Washington'),
    ('Petrified Forest', 'Arizona'),
    ('Pinnacles', 'California'),
    ('Redwood', 'California'),
    ('Rocky Mountain', 'Colorado'),
    ('Saguaro', 'Arizona'),
    ('Sequoia', 'California'),
    ('Shenandoah', 'Virginia'),
    ('Theodore Roosevelt', 'North Dakota'),
    ('Virgin Islands', 'U.S. Virgin Islands'),
    ('Voyageurs', 'Minnesota'),
    ('White Sands', 'New Mexico'),
    ('Wind Cave', 'South Dakota'),
    ('Wrangell–St. Elias', 'Alaska'),
    ('Yellowstone', 'Wyoming / Montana / Idaho'),
    ('Yosemite', 'California'),
    ('Zion', 'Utah'),
]

# Log entries that don't reduce to a park name via keyify()'s diacritic-fold
# and prefix matching in build_travel.py — kept explicit for the same reason
# merge_books.py's ALIASES is: a silent near-miss costs a visit its date.
# "Haleakala" needs no entry here; folding ā to a already matches it.
ALIASES = {
    'Hawaiian Volcanoes': 'Hawaiʻi Volcanoes',
}
