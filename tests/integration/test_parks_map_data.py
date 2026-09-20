"""Checks on the committed docs/_data/parks_map.json.

The map is generated once by a manual `--fetch` pass and then committed, so
nothing re-derives it on the way to the published page. That makes these
checks the only thing standing between a mistake in the projection and a map
with dots in the wrong places -- the kind of error that looks entirely fine
unless you happen to know where Zion is.

The central one is test_every_park_lands_in_its_own_state. It is what proves
the state outlines and the park markers came out of the same projection, since
their coordinates are only comparable if they did, and it is what checks
sixty-one hand-entered latitudes and longitudes without anyone reading them.
"""

import json
import math
import os
import re

import pytest

import build_parks_map as bpm
import gallery_data as gd
import national_parks as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAP_JSON = os.path.join(ROOT, 'docs', '_data', 'parks_map.json')
RENDER_JSON = os.path.join(ROOT, 'docs', '_data', 'gallery_render.json')
TRAVEL_JSON = os.path.join(ROOT, 'docs', '_data', 'travel.json')

POINT = re.compile(r'[ML](-?[\d.]+),(-?[\d.]+)')


def load(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


@pytest.fixture(scope='module')
def parks_map():
    if not os.path.exists(MAP_JSON):
        pytest.skip('parks_map.json not built; run build_parks_map.py --fetch')
    return load(MAP_JSON)


def parse_rings(path):
    """Read back the SVG path the generator writes, as lists of points.

    Deliberately parses the committed string rather than reaching into the
    generator's intermediate values: the path text is what ships.
    """
    rings = []
    for chunk in path.split('Z'):
        if not chunk:
            continue
        points = [(float(x), float(y)) for x, y in POINT.findall(chunk)]
        if len(points) >= 3:
            rings.append(points)
    return rings


def inside(point, rings):
    """Even-odd ray casting, which handles a state's holes and islands."""
    x, y = point
    crossings = 0
    for ring in rings:
        count = len(ring)
        for i in range(count):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % count]
            if (y1 > y) != (y2 > y):
                if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                    crossings += 1
    return crossings % 2 == 1


def distance_to(point, rings):
    """Shortest distance from a point to any edge of a set of rings."""
    x, y = point
    best = float('inf')
    for ring in rings:
        count = len(ring)
        for i in range(count):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % count]
            dx, dy = x2 - x1, y2 - y1
            if dx == 0 and dy == 0:
                best = min(best, math.hypot(x - x1, y - y1))
                continue
            t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


def declared_states(name):
    """The state(s) national_parks.py lists a park under."""
    subtitle = dict(np.ITEMS)[name]
    return [part.strip() for part in subtitle.split('/')]


class TestShape:
    def test_has_every_state_and_the_district(self, parks_map) -> None:
        assert len(parks_map['states']) == 51

    def test_no_territories_survived(self, parks_map) -> None:
        ids = {state['id'] for state in parks_map['states']}
        assert not ids & bpm.TERRITORY_FIPS

    def test_the_source_is_recorded(self, parks_map) -> None:
        # The geometry is third-party and public domain; saying where it came
        # from is the price of committing it.
        assert 'us-atlas' in parks_map['source']

    def test_every_state_has_drawable_path_data(self, parks_map) -> None:
        for state in parks_map['states']:
            assert state['path'].startswith('M')
            assert state['path'].endswith('Z')
            assert parse_rings(state['path'])


class TestProjection:
    def test_every_park_lands_in_its_own_state(self, parks_map) -> None:
        states = {state['name']: parse_rings(state['path'])
                  for state in parks_map['states']}
        wrong = []
        for park in parks_map['parks']:
            point = (park['x'], park['y'])
            wanted = declared_states(park['name'])
            known = [s for s in wanted if s in states]
            if any(inside(point, states[s]) for s in known):
                continue
            # Offshore and riverbank parks sit just outside the simplified
            # outline. A mistyped coordinate does not.
            nearest = min((distance_to(point, states[s]) for s in known),
                          default=float('inf'))
            if nearest > bpm.PROJECTION_TOLERANCE:
                wrong.append('%s: %.1fpx outside %s'
                             % (park['name'], nearest, ' / '.join(wanted)))
        assert not wrong, '; '.join(wrong)

    def test_every_park_is_on_the_canvas(self, parks_map) -> None:
        view = parks_map['view']
        for park in parks_map['parks']:
            assert 0 <= park['x'] <= view['width'], park['name']
            assert 0 <= park['y'] <= view['height'], park['name']

    def test_no_two_parks_share_a_position(self, parks_map) -> None:
        # Two markers on the same pixel means one is unclickable, and is a
        # likely sign of a copied coordinate.
        seen = {}
        for park in parks_map['parks']:
            key = (park['x'], park['y'])
            assert key not in seen, '%s and %s' % (seen.get(key), park['name'])
            seen[key] = park['name']

    def test_the_insets_are_reached(self, parks_map) -> None:
        # Alaska and Hawaii are drawn in boxes below and left of the mainland.
        # Without the sub-projections these ten parks would be off-canvas, so
        # this guards the routing as well as the projection.
        placed = {p['name']: (p['x'], p['y']) for p in parks_map['parks']}
        for name in ('Denali', 'Katmai', 'Haleakalā', 'Hawaiʻi Volcanoes'):
            assert placed[name][1] > parks_map['view']['height'] * 0.6, name


class TestCoverage:
    def test_every_park_on_the_checklist_has_a_coordinate(self) -> None:
        assert set(bpm.PARKS) == {name for name, _ in np.ITEMS}

    def test_the_map_carries_every_park_it_can(self, parks_map) -> None:
        drawn = {p['name'] for p in parks_map['parks']}
        assert drawn == set(bpm.PARKS) - set(bpm.UNPLOTTABLE)
        assert len(drawn) == len(np.ITEMS) - len(bpm.UNPLOTTABLE)

    def test_the_unplottable_parks_really_are_unplottable(self) -> None:
        # If Albers USA ever gains room for them, this fails and the pair
        # should come off the list rather than stay excluded out of habit.
        for name in bpm.UNPLOTTABLE:
            lat, lon = bpm.PARKS[name]
            assert bpm.route(lat, lon) is None, name

    def test_every_photographed_park_is_on_the_map(self, parks_map) -> None:
        photographed = {entry['park'] for entry in gd.load_gallery()
                        if entry.get('park')}
        drawn = {p['name'] for p in parks_map['parks']}
        assert photographed <= drawn

    def test_every_visited_park_is_on_the_map(self, parks_map) -> None:
        travel = load(TRAVEL_JSON)['checklists']['us_national_parks']['items']
        visited = {i['name'] for i in travel if i.get('visited')}
        drawn = {p['name'] for p in parks_map['parks']}
        assert visited <= drawn

    def test_every_photographed_park_has_a_colour(self) -> None:
        if not os.path.exists(RENDER_JSON):
            pytest.skip('gallery_render.json not built')
        parks = load(RENDER_JSON)['parks']
        for entry in gd.load_gallery():
            if entry.get('park'):
                assert entry['park'] in parks, entry['park']
