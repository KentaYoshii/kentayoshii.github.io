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


