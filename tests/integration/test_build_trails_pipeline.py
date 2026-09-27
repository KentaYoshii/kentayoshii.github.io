"""End-to-end tests for scripts/build_trails.py.

The script is offline and its output is committed, so what matters is that a
run turns the log into the data file the page renders, and that repeated runs
are byte-identical — CI's data job compares against the committed copy.
"""

import json

import pytest

import build_trails as bt


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    data = tmp_path / '_data'
    data.mkdir()
    log = tmp_path / 'trails.md'

    monkeypatch.setattr(bt, 'DATA', str(data))
    monkeypatch.setattr(bt, 'LOG_PATH', str(log))
    monkeypatch.setattr(bt, 'OUT_PATH', str(data / 'trails.json'))
    travel = data / 'travel.json'
    travel.write_text(json.dumps({'checklists': {'us_national_parks': {'items': [
        {'name': 'Zion'}, {'name': 'Yosemite'}]}}}), encoding='utf-8')
    monkeypatch.setattr(bt, 'TRAVEL_PATH', str(travel))

    class Workspace:
        path = data

        def write(self, body):
            log.write_text(body, encoding='utf-8')

        def read(self):
            return json.loads((data / 'trails.json').read_text(encoding='utf-8'))

        def hikes(self):
            """Every hike, in page order, out of its group."""
            return [t for g in self.read()['groups'] for t in g['trails']]

        def run(self):
            return bt.main()

    return Workspace()


LOG = '''# Trails

## 2026

### June
- Angels Landing — Zion National Park, UT — 5.4 mi — 1,488 ft

### July
- Mist Trail — Yosemite National Park, CA — 3 mi

## 2025

### September
- Timp Torne Trail — Harriman State Park, NY — 8 km — 300 m
'''


class TestBuild:
    def test_renders_every_logged_hike(self, workspace) -> None:
        workspace.write(LOG)
        assert workspace.run() == 0
        trails = workspace.hikes()
        assert [t['name'] for t in trails] == [
            'Mist Trail', 'Angels Landing', 'Timp Torne Trail']

    def test_sorted_newest_first(self, workspace) -> None:
        """A trail log reads as a diary, unlike the A-Z collection pages."""
        workspace.write(LOG)
        workspace.run()
        dates = [t['date'] for t in workspace.hikes()]
        assert dates == sorted(dates, reverse=True)

    def test_same_month_keeps_log_order(self, workspace) -> None:
        """Hikes in one month are shown as written, so a trip's hikes stay
        grouped by park rather than interleaved alphabetically."""
        workspace.write('## 2026\n### July\n'
                        '- Sol Duc Falls — Olympic\n'
                        '- Hoh River — Olympic\n'
                        '- Skyline Loop — Mount Rainier\n'
                        '- Bench Lake — Mount Rainier\n')
        workspace.run()
        assert [t['name'] for t in workspace.hikes()] == [
            'Sol Duc Falls', 'Hoh River', 'Skyline Loop', 'Bench Lake']

    def test_summary_totals(self, workspace) -> None:
        workspace.write(LOG)
        workspace.run()
        summary = workspace.read()['summary']
        assert summary['total'] == 3
        # 5.4 + 3 + (8 km -> 4.97) = 13.37, rounded to one decimal: a mile
        # total carrying two decimals would be false precision.
        assert summary['distance_mi'] == 13.4
        assert summary['distance_counted'] == 3
        # 1,488 ft + (300 m -> 984 ft); Mist Trail has no gain logged and is
        # left out of the count rather than counted as zero.
        assert summary['elevation_ft'] == 2472
        assert summary['elevation_text'] == '2,472'
        assert summary['elevation_counted'] == 2
        assert summary['by_year'] == [{'year': '2026', 'count': 2},
                                      {'year': '2025', 'count': 1}]

    def test_groups_and_park_totals(self, workspace) -> None:
        workspace.write(LOG)
        workspace.run()
        payload = workspace.read()
        assert [(g['year'], g['label'], g['park']) for g in payload['groups']] == [
            ('2026', 'Yosemite', 'Yosemite'),
            ('2026', 'Zion', 'Zion'),
            ('2025', 'Harriman State Park', None),
        ]
        assert sorted(payload['parks']) == ['Yosemite', 'Zion']
        assert payload['parks']['Zion']['elevation_text'] == '1,488'

    def test_runs_without_travel_json(self, workspace, monkeypatch, tmp_path) -> None:
        """Hikes just go unmatched; the page still renders them."""
        monkeypatch.setattr(bt, 'TRAVEL_PATH', str(tmp_path / 'absent.json'))
        workspace.write(LOG)
        assert workspace.run() == 0
        payload = workspace.read()
        assert payload['parks'] == {}
        assert len(payload['groups']) == 3

    def test_is_byte_stable_across_runs(self, workspace) -> None:
        """What CI's `git diff --quiet -- docs/_data` relies on."""
        workspace.write(LOG)
        workspace.run()
        snapshot = (workspace.path / 'trails.json').read_bytes()
        workspace.run()
        workspace.run()
        assert (workspace.path / 'trails.json').read_bytes() == snapshot

    def test_empty_log_is_not_an_error(self, workspace) -> None:
        workspace.write('# Trails\n\n## 2026\n')
        assert workspace.run() == 0
        payload = workspace.read()
        assert payload['groups'] == []
        assert payload['summary']['total'] == 0
        assert payload['summary']['elevation_ft'] == 0
