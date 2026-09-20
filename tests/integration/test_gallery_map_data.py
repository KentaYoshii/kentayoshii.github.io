"""Checks on the committed docs/_data/gallery_map.json.

The map is generated once by a manual `--fetch` pass and then committed, so
nothing re-derives it on the way to the published page. That makes these
checks the only thing standing between a mistake in the projection and a map
with dots in the wrong places, which is exactly the kind of error that looks
fine unless you know where Zion is.

The central one is test_every_park_sits_inside_its_own_state: it is what
proves the state outlines and the park markers came out of the same
projection, since the coordinates are only comparable if they did.
"""

import json
import os
import re

import pytest

import build_gallery_map as bgm
import gallery_data as gd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAP_JSON = os.path.join(ROOT, 'docs', '_data', 'gallery_map.json')
RENDER_JSON = os.path.join(ROOT, 'docs', '_data', 'gallery_render.json')
TRAVEL_JSON = os.path.join(ROOT, 'docs', '_data', 'travel.json')

POINT = re.compile(r'[ML](-?[\d.]+),(-?[\d.]+)')


def load(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


@pytest.fixture(scope='module')
def gallery_map():
    if not os.path.exists(MAP_JSON):
        pytest.skip('gallery_map.json not built; run build_gallery_map.py --fetch')
    return load(MAP_JSON)


def parse_rings(path):
    """Read back the SVG path this script writes, as lists of points.

    Deliberately parses the committed string rather than reaching into the
    generator's intermediate values: what ships is the path text, so that is
    what should be checked.
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
                crossing_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                if x < crossing_x:
                    crossings += 1
    return crossings % 2 == 1


class TestShape:
    def test_has_every_state_and_the_district(self, gallery_map) -> None:
        assert len(gallery_map['states']) == 51

    def test_no_territories_survived(self, gallery_map) -> None:
        ids = {state['id'] for state in gallery_map['states']}
        assert not ids & bgm.TERRITORY_FIPS

    def test_the_source_is_recorded(self, gallery_map) -> None:
        # The geometry is third-party and public domain; saying where it came
        # from is the price of committing it.
        assert 'us-atlas' in gallery_map['source']

    def test_every_state_has_drawable_path_data(self, gallery_map) -> None:
        for state in gallery_map['states']:
            assert state['path'].startswith('M')
            assert state['path'].endswith('Z')
            assert parse_rings(state['path'])


class TestProjection:
    def test_every_park_sits_inside_its_own_state(self, gallery_map) -> None:
        states = {state['id']: state for state in gallery_map['states']}
        misplaced = []
        for park in gallery_map['parks']:
            state = states[park['state']]
            if not inside((park['x'], park['y']), parse_rings(state['path'])):
                misplaced.append('%s is not inside %s'
                                 % (park['name'], state['name']))
        assert not misplaced, '; '.join(misplaced)

    def test_every_park_is_on_the_canvas(self, gallery_map) -> None:
        view = gallery_map['view']
        for park in gallery_map['parks']:
            assert 0 <= park['x'] <= view['width'], park['name']
            assert 0 <= park['y'] <= view['height'], park['name']

    def test_the_two_hawaii_parks_reach_the_inset(self, gallery_map) -> None:
        # Below and left of the mainland's centre is where albersUsa puts the
        # Hawaii inset. Without the inset these two would be off-canvas, so
        # this is a regression guard on the sub-projection being applied.
        hawaii = [p for p in gallery_map['parks'] if p['state'] == '15']
        assert len(hawaii) == 2
        for park in hawaii:
            assert park['y'] > gallery_map['view']['height'] * 0.8, park['name']


class TestJoinsToTheRestOfTheSite:
    def test_every_mapped_park_is_a_visited_park(self) -> None:
        travel = load(TRAVEL_JSON)['checklists']['us_national_parks']['items']
        visited = {item['name'] for item in travel if item.get('visited')}
        assert set(bgm.PARKS) <= visited

    def test_every_photographed_park_is_on_the_map(self) -> None:
        # A park with photos but no marker would leave a section the map
        # cannot reach.
        photographed = {entry['park'] for entry in gd.load_gallery()
                        if entry.get('park')}
        assert photographed == set(bgm.PARKS)

    def test_every_marker_has_a_colour_to_be_drawn_in(self) -> None:
        if not os.path.exists(RENDER_JSON):
            pytest.skip('gallery_render.json not built')
        parks = load(RENDER_JSON)['parks']
        for name in bgm.PARKS:
            assert name in parks, name
            assert parks[name]['accent'].startswith('#')
            assert parks[name]['accent_dark'].startswith('#')
