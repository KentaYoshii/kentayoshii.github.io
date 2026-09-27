"""Unit tests for scripts/build_trails.py.

The log parser is where the sharp edges are: a separator that also occurs
inside trail names, distance and elevation units that share a letter, and
fields that are recognised by content rather than position.
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


class TestParseElevation:
    @pytest.mark.parametrize('text, feet', [
        ('4,350 ft', 4350),
        ('4350ft', 4350),
        ('1,488 feet', 1488),
        ('450 m', 1476),
        ('450 metres', 1476),
        ('450 meters', 1476),
    ])
    def test_units(self, text: str, feet: int) -> None:
        assert bt.parse_elevation(text) == feet

    @pytest.mark.parametrize('text', ['', None, '5.4 mi', '10 km', 'Zion, UT',
                                      '4350', '1.2.3 ft'])
    def test_unparseable_is_none(self, text) -> None:
        """Miles and kilometres in particular: 'm' is metres only when it is
        not the start of 'mi'."""
        assert bt.parse_elevation(text) is None


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

    def test_elevation_gain(self, tmp_path) -> None:
        path = self.write(tmp_path, '## 2025\n- Paintbrush–Cascade Canyon Loop'
                                    ' — Grand Teton, WY — 19 mi — 4,350 ft\n')
        entry, = bt.parse_log(path)
        assert entry['name'] == 'Paintbrush–Cascade Canyon Loop'
        assert entry['place'] == 'Grand Teton, WY'
        assert entry['distance_mi'] == 19.0
        assert entry['elevation_ft'] == 4350
        assert entry['elevation_text'] == '4,350 ft'

    def test_elevation_without_a_place(self, tmp_path) -> None:
        path = self.write(tmp_path, '## 2026\n- Some Ridge — 4 mi — 900 ft\n')
        entry, = bt.parse_log(path)
        assert entry['place'] == ''
        assert (entry['distance_mi'], entry['elevation_ft']) == (4.0, 900)

    def test_elevation_is_optional(self, tmp_path) -> None:
        path = self.write(tmp_path, '## 2026\n- Some Ridge — Zion — 4 mi\n')
        entry, = bt.parse_log(path)
        assert entry['elevation_ft'] is None
        assert entry['elevation_text'] == ''

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


PARKS = {'Glacier', 'Rocky Mountain', 'Hawaiʻi Volcanoes'}


class TestParkOf:
    @pytest.mark.parametrize('place, park', [
        ('Glacier National Park, MT', 'Glacier'),
        ('Rocky Mountain National Park, CO', 'Rocky Mountain'),
        ('Hawaiʻi Volcanoes National Park, HI', 'Hawaiʻi Volcanoes'),
        # The bare checklist name is accepted too.
        ('Glacier', 'Glacier'),
    ])
    def test_matches_the_checklist_name(self, place: str, park: str) -> None:
        assert bt.park_of(place, PARKS) == park

    @pytest.mark.parametrize('place', [
        'Harriman State Park, NY',
        # Close is not enough: the parks page keys on the exact name.
        'Hawaii Volcanoes National Park, HI',
        'Glacier Point, CA',
        '',
        None,
    ])
    def test_anything_else_is_none(self, place) -> None:
        assert bt.park_of(place, PARKS) is None


class TestLabelOf:
    def test_park_name_wins(self) -> None:
        assert bt.label_of('Glacier National Park, MT', 'Glacier') == 'Glacier'

    def test_outside_a_park_uses_the_place(self) -> None:
        assert bt.label_of('Harriman State Park, NY', None) == 'Harriman State Park'

    def test_no_place(self) -> None:
        assert bt.label_of('', None) == ''


class TestMilesText:
    @pytest.mark.parametrize('miles, text', [
        (95.4, '95.4'), (5.0, '5'), (44.0, '44'), (32.24, '32.2'), (0, '0'),
    ])
    def test_format(self, miles: float, text: str) -> None:
        assert bt.miles_text(miles) == text


def hike(name, date, park, distance=None, elevation=None):
    return {'name': name, 'date': date, 'year': date[:4], 'month': 'M',
            'park': park, 'label': park or 'Elsewhere',
            'distance_mi': distance, 'elevation_ft': elevation}


class TestGroup:
    def test_consecutive_hikes_in_one_park_and_month_are_one_group(self) -> None:
        groups = bt.group([
            hike('a', '2026-09', 'Glacier', 10, 2000),
            hike('b', '2026-09', 'Glacier', 5.5, 1000),
            hike('c', '2026-09', 'Rocky Mountain', 9, 2400),
        ])
        assert [(g['label'], g['count']) for g in groups] == [
            ('Glacier', 2), ('Rocky Mountain', 1)]
        assert groups[0]['distance_text'] == '15.5'
        assert groups[0]['elevation_text'] == '3,000'

    def test_a_park_visited_twice_is_two_groups(self) -> None:
        """The page is a diary; a second trip is a second heading."""
        groups = bt.group([
            hike('a', '2026-09', 'Glacier'),
            hike('b', '2024-07', 'Glacier'),
        ])
        assert len(groups) == 2

    def test_only_the_most_recent_group_of_a_park_is_flagged(self) -> None:
        """It carries the id the parks page links to; ids must be unique."""
        groups = bt.group([
            hike('a', '2026-09', 'Glacier'),
            hike('b', '2025-06', 'Rocky Mountain'),
            hike('c', '2024-07', 'Glacier'),
        ])
        assert [g['first_of_park'] for g in groups] == [True, True, False]

    def test_hikes_outside_a_park_are_never_flagged(self) -> None:
        groups = bt.group([hike('a', '2026-09', None)])
        assert groups[0]['first_of_park'] is False
        assert groups[0]['park'] is None

    def test_missing_numbers_count_as_nothing(self) -> None:
        group, = bt.group([hike('a', '2026-09', 'Glacier'),
                           hike('b', '2026-09', 'Glacier', 4, 300)])
        assert (group['count'], group['distance_mi'], group['elevation_ft']) == (2, 4, 300)


class TestByPark:
    def test_totals_across_visits(self) -> None:
        parks = bt.by_park([
            hike('a', '2026-09', 'Glacier', 10, 2000),
            hike('b', '2024-07', 'Glacier', 5, 500),
            hike('c', '2026-09', None, 3, 100),
        ])
        assert list(parks) == ['Glacier']
        assert parks['Glacier']['count'] == 2
        assert parks['Glacier']['distance_text'] == '15'
        assert parks['Glacier']['elevation_text'] == '2,500'


class TestLoadParkNames:
    def test_reads_the_checklist(self, tmp_path) -> None:
        path = tmp_path / 'travel.json'
        path.write_text('{"checklists": {"us_national_parks": {"items": '
                        '[{"name": "Zion"}, {"name": "Glacier"}]}}}', encoding='utf-8')
        assert bt.load_park_names(str(path)) == {'Zion', 'Glacier'}

    @pytest.mark.parametrize('body', [None, '{ oh no', '{}', '{"checklists": []}'])
    def test_missing_or_malformed_is_empty(self, tmp_path, body) -> None:
        path = tmp_path / 'travel.json'
        if body is not None:
            path.write_text(body, encoding='utf-8')
        assert bt.load_park_names(str(path)) == set()


class TestUnmatchedParks:
    def trails(self, *places):
        return [{'place': p, 'park': bt.park_of(p, PARKS)} for p in places]

    def test_a_typo_is_reported_with_a_suggestion(self) -> None:
        found = bt.unmatched_parks(self.trails('Glacer National Park, MT'), PARKS)
        assert found == [('Glacer National Park, MT', 'Glacier')]

    def test_matched_parks_and_other_places_are_not_reported(self) -> None:
        found = bt.unmatched_parks(self.trails(
            'Glacier National Park, MT', 'Harriman State Park, NY', ''), PARKS)
        assert found == []

    def test_no_close_match_has_no_suggestion(self) -> None:
        found = bt.unmatched_parks(self.trails('Acadia National Park, ME'), PARKS)
        assert found == [('Acadia National Park, ME', None)]

    @pytest.mark.parametrize('place', [
        'Tongariro National Park, New Zealand',
        'Aoraki/Mount Cook National Park, NZ, New Zealand',
        'Banff National Park, Alberta',
    ])
    def test_a_park_outside_the_us_is_not_reported(self, place: str) -> None:
        """The checklist is US parks only; these are not typos."""
        assert bt.unmatched_parks(self.trails(place), PARKS) == []

    def test_a_typo_with_no_region_is_still_reported(self) -> None:
        found = bt.unmatched_parks(self.trails('Glacer National Park'), PARKS)
        assert found == [('Glacer National Park', 'Glacier')]

    def test_each_place_is_reported_once(self) -> None:
        found = bt.unmatched_parks(self.trails('Glacer National Park, MT',
                                               'Glacer National Park, MT'), PARKS)
        assert len(found) == 1


def logged(name, park, distance=None, elevation=None):
    return {'name': name, 'park': park, 'distance_mi': distance,
            'distance_text': '%g mi' % distance if distance else '',
            'elevation_ft': elevation,
            'elevation_text': '{:,} ft'.format(elevation) if elevation else ''}


class TestGainShare:
    def test_relative_to_the_biggest_climb(self) -> None:
        trails = [logged('a', 'P', elevation=4000), logged('b', 'P', elevation=1000)]
        bt.add_gain_share(trails)
        assert [t['gain_pct'] for t in trails] == [100, 25]

    def test_a_tiny_gain_still_shows(self) -> None:
        """49 ft against 4,232 ft rounds to 1%, not to an invisible 0%."""
        trails = [logged('a', 'P', elevation=4232), logged('b', 'P', elevation=10)]
        bt.add_gain_share(trails)
        assert trails[1]['gain_pct'] == 1

    def test_no_gain_logged_is_none_not_zero(self) -> None:
        trails = [logged('a', 'P', elevation=4000), logged('b', 'P')]
        bt.add_gain_share(trails)
        assert trails[1]['gain_pct'] is None

    def test_nothing_logged_at_all(self) -> None:
        trails = [logged('a', 'P')]
        bt.add_gain_share(trails)
        assert trails[0]['gain_pct'] is None
        bt.add_gain_share([])


class TestRecords:
    def test_picks_each_record(self) -> None:
        trails = [logged('Short steep', 'Zion', 5, 3000),
                  logged('Long flat', 'Glacier', 20, 500),
                  logged('Middle', 'Glacier', 10, 1000)]
        out = bt.records(trails, bt.by_park(trails))
        assert out['longest'] == {'name': 'Long flat', 'park': 'Glacier', 'text': '20 mi'}
        assert out['climb'] == {'name': 'Short steep', 'park': 'Zion', 'text': '3,000 ft'}
        assert out['park'] == {'name': 'Glacier', 'park': 'Glacier', 'text': '30 mi'}

    def test_a_tie_goes_to_the_more_recent(self) -> None:
        """Trails arrive newest first."""
        trails = [logged('Newer', 'Zion', 10), logged('Older', 'Zion', 10)]
        assert bt.records(trails, {})['longest']['name'] == 'Newer'

    def test_an_empty_log_has_no_records(self) -> None:
        assert bt.records([], {}) == {}

    def test_a_record_needs_its_number(self) -> None:
        out = bt.records([logged('No numbers', None)], {})
        assert out == {}


class TestAttachPhotos:
    def trails(self):
        return [{'name': 'Skyline Trail', 'park': 'Mount Rainier'},
                {'name': 'Skyline Trail', 'park': 'Other Park'},
                {'name': 'Avalanche Lake', 'park': 'Glacier'}]

    def test_matches_on_park_and_name_together(self) -> None:
        """Two parks can each have a hike with the same name."""
        trails = self.trails()
        stray = bt.attach_photos(trails, [
            {'image': 'a.jpeg', 'park': 'Mount Rainier', 'trail': 'Skyline Trail'},
            {'image': 'b.jpeg', 'park': 'Other Park', 'trail': 'Skyline Trail'},
        ])
        assert stray == []
        assert [t['photos'] for t in trails] == [['a.jpeg'], ['b.jpeg'], []]

    def test_keeps_gallery_order(self) -> None:
        trails = self.trails()
        bt.attach_photos(trails, [
            {'image': 'z.jpeg', 'park': 'Glacier', 'trail': 'Avalanche Lake'},
            {'image': 'a.jpeg', 'park': 'Glacier', 'trail': 'Avalanche Lake'},
        ])
        assert trails[2]['photos'] == ['z.jpeg', 'a.jpeg']

    def test_a_trail_in_the_wrong_park_is_stray(self) -> None:
        photo = {'image': 'a.jpeg', 'park': 'Zion', 'trail': 'Avalanche Lake'}
        assert bt.attach_photos(self.trails(), [photo]) == [photo]

    def test_photos_without_a_trail_are_ignored(self) -> None:
        trails = self.trails()
        assert bt.attach_photos(trails, [{'image': 'a.jpeg', 'park': 'Glacier'}]) == []
        assert all(t['photos'] == [] for t in trails)

    def test_path_prefixes_are_dropped(self) -> None:
        trails = self.trails()
        bt.attach_photos(trails, [{'image': 'assets/x/a.jpeg', 'park': 'Glacier',
                                   'trail': 'Avalanche Lake'}])
        assert trails[2]['photos'] == ['a.jpeg']


class TestRealGallery:
    """The committed gallery.yml against the committed trail log."""

    def test_every_photo_trail_is_a_logged_hike(self) -> None:
        trails = bt.parse_log()
        names = bt.load_park_names()
        for trail in trails:
            trail['park'] = bt.park_of(trail['place'], names)
        stray = bt.attach_photos(trails, bt.load_photos())
        assert [(p['image'], p['trail']) for p in stray] == []
