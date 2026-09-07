"""Unit tests for scripts/build_trails.py.

The log parser and the OSM tag handling are where the sharp edges are: a
separator that also occurs inside trail names, distance units, and a tag whose
meaning changes depending on which kind of OSM object carries it.
"""

import pytest

import build_trails as bt


class TestParseDistance:
    @pytest.mark.parametrize('text, miles', [
        ('6.2 mi', 6.2),
        ('6.2mi', 6.2),
        ('5 miles', 5.0),
        ('3 mile', 3.0),
        ('10 km', 6.21),
        ('8km', 4.97),
    ])
    def test_units(self, text: str, miles: float) -> None:
        assert bt.parse_distance(text) == miles

    @pytest.mark.parametrize('text', ['', None, 'a while', 'Zion, UT', '6.2'])
    def test_unparseable_is_none(self, text) -> None:
        assert bt.parse_distance(text) is None


class TestAreaOf:
    @pytest.mark.parametrize('place, area', [
        ('Zion National Park, UT', 'Zion National Park'),
        ('Harriman State Park, NY', 'Harriman State Park'),
        ('Yosemite', 'Yosemite'),
        ('', ''),
    ])
    def test_takes_the_part_before_the_comma(self, place: str, area: str) -> None:
        assert bt.area_of(place) == area


class TestParseLog:
    def write(self, tmp_path, body):
        path = tmp_path / 'trails.md'
        path.write_text(body, encoding='utf-8')
        return str(path)

    def test_full_entry(self, tmp_path) -> None:
        path = self.write(tmp_path, '## 2026\n### June\n'
                                    '- Angels Landing — Zion National Park, UT — 5.4 mi\n')
        entry, = bt.parse_log(path)
        assert entry['name'] == 'Angels Landing'
        assert entry['place'] == 'Zion National Park, UT'
        assert entry['area'] == 'Zion National Park'
        assert entry['distance_mi'] == 5.4
        assert entry['year'] == '2026'
        assert entry['month'] == 'June'
        assert entry['date'] == '2026-06'

    @pytest.mark.parametrize('separator', ['—', '–', '--'])
    def test_accepted_separators(self, tmp_path, separator: str) -> None:
        line = '- Mist Trail {s} Yosemite {s} 3 mi\n'.format(s=separator)
        path = self.write(tmp_path, '## 2026\n' + line)
        entry, = bt.parse_log(path)
        assert (entry['name'], entry['place']) == ('Mist Trail', 'Yosemite')

    def test_a_hyphen_inside_a_name_is_not_a_separator(self, tmp_path) -> None:
        """Real trail names contain ' - ' — splitting on it would cut
        'Suffern - Bear Mountain Trail' in half."""
        path = self.write(tmp_path, '## 2025\n'
                                    '- Suffern - Bear Mountain Trail — Harriman, NY — 4 mi\n')
        entry, = bt.parse_log(path)
        assert entry['name'] == 'Suffern - Bear Mountain Trail'
        assert entry['place'] == 'Harriman, NY'

    def test_name_only(self, tmp_path) -> None:
        path = self.write(tmp_path, '## 2026\n- Some Ridge\n')
        entry, = bt.parse_log(path)
        assert entry['name'] == 'Some Ridge'
        assert entry['place'] == ''
        assert entry['distance_mi'] is None

    def test_name_and_distance_without_a_place(self, tmp_path) -> None:
        """Two fields where the second parses as a distance is a distance,
        not a place called '4 mi'."""
        path = self.write(tmp_path, '## 2026\n- Some Ridge — 4 mi\n')
        entry, = bt.parse_log(path)
        assert entry['place'] == ''
        assert entry['distance_mi'] == 4.0

    def test_month_is_optional(self, tmp_path) -> None:
        """No month sorts to the start of its year, as in build_movies.py."""
        path = self.write(tmp_path, '## 2026\n- Some Ridge — Zion\n')
        entry, = bt.parse_log(path)
        assert entry['month'] is None
        assert entry['date'] == '2026-00'

    def test_entries_before_any_year_are_ignored(self, tmp_path) -> None:
        """Everything above the first '## <year>' is prose, including the
        format example in the log's own header."""
        path = self.write(tmp_path,
                          '# Trails\n\n- <trail name> — <where> — <distance>\n\n'
                          '## 2026\n- Real Trail — Zion\n')
        entries = bt.parse_log(path)
        assert [e['name'] for e in entries] == ['Real Trail']

    def test_a_non_year_heading_stops_collection(self, tmp_path) -> None:
        path = self.write(tmp_path,
                          '## 2026\n- Kept — Zion\n'
                          '## Notes\n- Dropped — Zion\n')
        assert [e['name'] for e in bt.parse_log(path)] == ['Kept']

    def test_empty_log(self, tmp_path) -> None:
        assert bt.parse_log(self.write(tmp_path, '# Trails\n\n## 2026\n')) == []


class TestBlaze:
    @pytest.mark.parametrize('tags, expected', [
        # osmc:symbol is waycolour:background:foreground[:...]; only the
        # waycolour is the paint on the tree.
        ({'osmc:symbol': 'blue:blue'}, 'blue'),
        ({'osmc:symbol': 'yellow::yellow_stripe'}, 'yellow'),
        ({'osmc:symbol': 'red:white:red_dot'}, 'red'),
        ({'osmc:symbol': 'white::white_stripe'}, 'white'),
        # A plain colour tag is the fallback.
        ({'colour': '#80FECE'}, '#80FECE'),
        # osmc:symbol wins when both are present.
        ({'osmc:symbol': 'blue:blue', 'colour': 'red'}, 'blue'),
    ])
    def test_extracts_the_way_colour(self, tags: dict, expected: str) -> None:
        assert bt.blaze_of(tags) == expected

    @pytest.mark.parametrize('tags', [
        {},
        {'colour': ''},
        {'osmc:symbol': ''},
        # A leading colon means no waycolour was recorded.
        {'osmc:symbol': ':white:blue_dot'},
        {'sac_scale': 'hiking'},
    ])
    def test_no_blaze(self, tags: dict) -> None:
        assert bt.blaze_of(tags) is None


class TestCacheKey:
    def test_same_name_in_two_parks_is_two_trails(self) -> None:
        """'Skyline Trail' exists in many parks."""
        a = bt.cache_key({'name': 'Skyline Trail', 'area': 'Mount Rainier National Park'})
        b = bt.cache_key({'name': 'Skyline Trail', 'area': 'Acadia National Park'})
        assert a != b

    def test_is_insensitive_to_case_and_punctuation(self) -> None:
        a = bt.cache_key({'name': "Angel's Landing", 'area': 'Zion National Park'})
        b = bt.cache_key({'name': 'ANGELS LANDING', 'area': 'zion national park'})
        assert a == b


class TestDecorate:
    def base(self, **over):
        entry = {'name': 'T', 'place': 'P', 'year': '2026', 'month': 'June',
                 'date': '2026-06', 'distance_mi': 5.0, 'distance_text': '5 mi',
                 'area': 'P'}
        entry.update(over)
        return entry

    def test_unresolved_trail_still_renders(self) -> None:
        out = bt.decorate(self.base(), {})
        assert out['resolved'] is False
        assert out['name'] == 'T'
        assert out['distance_text'] == '5 mi'
        assert out['blaze'] is None

    def test_sac_scale_is_relabelled(self) -> None:
        """The raw values read as jargon on a personal site."""
        assert bt.decorate(self.base(), {'sac_scale': 'hiking'})['difficulty'] == 'easy'
        assert bt.decorate(self.base(), {'sac_scale': 'alpine_hiking'})['difficulty'] == 'alpine'

    def test_an_unknown_sac_scale_is_dropped_not_shown_raw(self) -> None:
        assert bt.decorate(self.base(), {'sac_scale': 'via_ferrata'})['difficulty'] is None

    def test_official_distance_is_converted_from_km(self) -> None:
        out = bt.decorate(self.base(), {'distance': '4.8'})
        assert out['official_distance_mi'] == 2.98

    @pytest.mark.parametrize('value', ['', 'about 5', None])
    def test_an_unparseable_official_distance_is_dropped(self, value) -> None:
        assert bt.decorate(self.base(), {'distance': value})['official_distance_mi'] is None


class TestLookupTagMerging:
    """lookup() merges tags across a trail's many OSM objects."""

    def elements(self):
        return {'elements': [
            # A way listed first, deliberately: relations must still win.
            {'type': 'way', 'id': 1,
             'tags': {'distance': '4.8', 'surface': 'ground', 'sac_scale': 'hiking'}},
            {'type': 'relation', 'id': 2,
             'tags': {'distance': '27.8', 'network': 'lwn'}},
            {'type': 'way', 'id': 3, 'tags': {'surface': 'rock'}},
        ]}

    def test_distance_comes_only_from_the_relation(self, monkeypatch) -> None:
        """On a way, 'distance' is one segment's length — merging it produced
        an official 2.98 mi against a logged 17.3 mi on the Hoh River Trail."""
        monkeypatch.setattr(bt, 'overpass', lambda n, a: self.elements())
        assert bt.lookup('T', 'A')['distance'] == '27.8'

    def test_a_way_only_tag_is_still_collected(self, monkeypatch) -> None:
        monkeypatch.setattr(bt, 'overpass', lambda n, a: self.elements())
        tags = bt.lookup('T', 'A')
        assert tags['sac_scale'] == 'hiking'
        assert tags['surface'] == 'ground'      # first way wins over the later one

    def test_distance_is_dropped_when_only_ways_carry_it(self, monkeypatch) -> None:
        monkeypatch.setattr(bt, 'overpass', lambda n, a: {'elements': [
            {'type': 'way', 'id': 1, 'tags': {'distance': '4.8', 'surface': 'ground'}},
        ]})
        tags = bt.lookup('T', 'A')
        assert 'distance' not in tags
        assert tags['surface'] == 'ground'

    def test_untracked_tags_are_discarded(self, monkeypatch) -> None:
        """OSM's long tail should not end up in the committed data file."""
        monkeypatch.setattr(bt, 'overpass', lambda n, a: {'elements': [
            {'type': 'way', 'id': 1, 'tags': {'surface': 'ground', 'width': '1.5',
                                              'source': 'survey', 'foot': 'yes'}},
        ]})
        assert set(bt.lookup('T', 'A')) == {'surface', 'osm_elements'}

    def test_no_match_is_an_empty_dict(self, monkeypatch) -> None:
        monkeypatch.setattr(bt, 'overpass', lambda n, a: {'elements': []})
        assert bt.lookup('T', 'A') == {}
