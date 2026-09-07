"""End-to-end tests for scripts/build_trails.py.

Same contract as build_covers.py, so the same things matter: the offline pass
must never touch the network, and a --fetch run that dies partway must keep
what it resolved and still write a usable data file.

Every network call is stubbed; nothing here reaches Overpass.
"""

import json
import urllib.error

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
    monkeypatch.setattr(bt, 'CACHE_PATH', str(data / 'trails_osm.json'))
    monkeypatch.setattr(bt, 'REQUEST_PAUSE', 0)

    class Workspace:
        path = data

        def write(self, body, cache=None):
            log.write_text(body, encoding='utf-8')
            if cache is not None:
                (data / 'trails_osm.json').write_text(
                    json.dumps(cache), encoding='utf-8')

        def read(self, name):
            return json.loads((data / name).read_text(encoding='utf-8'))

        def run(self, *argv):
            return bt.main(list(argv))

    return Workspace()


@pytest.fixture
def no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError('unexpected network call')
    monkeypatch.setattr(bt, 'overpass', boom)


LOG = '''# Trails

## 2026

### June
- Angels Landing — Zion National Park, UT — 5.4 mi

### July
- Mist Trail — Yosemite National Park, CA — 3 mi

## 2025

### September
- Timp Torne Trail — Harriman State Park, NY — 8 km
'''


class TestOfflinePass:
    def test_makes_no_requests(self, workspace, no_network) -> None:
        workspace.write(LOG)
        assert workspace.run() == 0

    def test_renders_every_logged_hike(self, workspace, no_network) -> None:
        workspace.write(LOG)
        workspace.run()
        trails = workspace.read('trails.json')['trails']
        assert [t['name'] for t in trails] == [
            'Mist Trail', 'Angels Landing', 'Timp Torne Trail']

    def test_sorted_newest_first(self, workspace, no_network) -> None:
        """A trail log reads as a diary, unlike the A-Z collection pages."""
        workspace.write(LOG)
        workspace.run()
        dates = [t['date'] for t in workspace.read('trails.json')['trails']]
        assert dates == sorted(dates, reverse=True)

    def test_merges_cached_osm_tags(self, workspace, no_network) -> None:
        workspace.write(LOG, cache={
            'timptornetrail|harrimanstatepark': {'osmc:symbol': 'blue:blue'},
            'angelslanding|zionnationalpark': {'sac_scale': 'alpine_hiking',
                                               'surface': 'ground'},
        })
        workspace.run()
        by_name = {t['name']: t for t in workspace.read('trails.json')['trails']}
        assert by_name['Timp Torne Trail']['blaze'] == 'blue'
        assert by_name['Angels Landing']['difficulty'] == 'alpine'
        assert by_name['Mist Trail']['resolved'] is False

    def test_summary_totals(self, workspace, no_network) -> None:
        workspace.write(LOG, cache={'misttrail|yosemitenationalpark': {'surface': 'rock'}})
        workspace.run()
        summary = workspace.read('trails.json')['summary']
        assert summary['total'] == 3
        # 5.4 + 3 + (8 km -> 4.97) = 13.37, rounded to one decimal: a mile
        # total carrying two decimals would be false precision.
        assert summary['distance_mi'] == 13.4
        assert summary['distance_counted'] == 3
        assert summary['resolved'] == 1
        assert summary['by_year'] == [{'year': '2026', 'count': 2},
                                      {'year': '2025', 'count': 1}]

    def test_is_byte_stable_across_runs(self, workspace, no_network) -> None:
        """What CI's `git diff --quiet -- docs/_data` relies on."""
        workspace.write(LOG, cache={'misttrail|yosemitenationalpark': {'surface': 'rock'}})
        workspace.run()
        snapshot = {n: (workspace.path / n).read_bytes()
                    for n in ('trails.json', 'trails_osm.json')}
        workspace.run()
        workspace.run()
        for name, blob in snapshot.items():
            assert (workspace.path / name).read_bytes() == blob, name

    def test_prunes_trails_no_longer_logged(self, workspace, no_network) -> None:
        workspace.write(LOG, cache={
            'misttrail|yosemitenationalpark': {'surface': 'rock'},
            'retiredtrail|somewhere': {'surface': 'gravel'},
        })
        workspace.run()
        assert 'retiredtrail|somewhere' not in workspace.read('trails_osm.json')

    def test_empty_log_is_not_an_error(self, workspace, no_network) -> None:
        workspace.write('# Trails\n\n## 2026\n')
        assert workspace.run() == 0
        payload = workspace.read('trails.json')
        assert payload['trails'] == []
        assert payload['summary']['total'] == 0

    def test_survives_a_corrupt_cache(self, workspace, no_network) -> None:
        workspace.write(LOG)
        (workspace.path / 'trails_osm.json').write_text('{ oh no', encoding='utf-8')
        assert workspace.run() == 0


class TestFetchPass:
    def test_looks_up_only_uncached_trails(self, workspace, monkeypatch) -> None:
        asked = []

        def fake_overpass(name, area):
            asked.append((name, area))
            return {'elements': [{'type': 'way', 'id': 1,
                                  'tags': {'surface': 'ground'}}]}

        monkeypatch.setattr(bt, 'overpass', fake_overpass)
        workspace.write(LOG, cache={'misttrail|yosemitenationalpark': {'surface': 'rock'}})
        workspace.run('--fetch')

        assert ('Mist Trail', 'Yosemite National Park') not in asked
        assert len(asked) == 2

    def test_a_cached_miss_is_not_retried(self, workspace, no_network) -> None:
        """An empty dict means 'asked, nothing there'."""
        workspace.write('## 2026\n- Obscure Trail — Zion National Park\n',
                        cache={'obscuretrail|zionnationalpark': {}})
        assert workspace.run('--fetch') == 0

    def test_a_trail_with_no_place_is_skipped(self, workspace, no_network) -> None:
        """There is nothing to scope an area search to."""
        workspace.write('## 2026\n- Just A Name\n')
        assert workspace.run('--fetch') == 0
        assert workspace.read('trails.json')['trails'][0]['resolved'] is False

    def test_a_failure_keeps_results_and_still_writes(self, workspace,
                                                      monkeypatch) -> None:
        calls = {'n': 0}

        def flaky(name, area):
            calls['n'] += 1
            if calls['n'] == 1:
                return {'elements': [{'type': 'way', 'id': 1,
                                      'tags': {'surface': 'ground'}}]}
            raise urllib.error.URLError('connection reset')

        monkeypatch.setattr(bt, 'overpass', flaky)
        workspace.write(LOG)

        assert workspace.run('--fetch') == 1
        # The data file is written regardless, so the partial result shows up
        # without needing a second offline run.
        assert workspace.read('trails.json')['summary']['resolved'] == 1
        assert len(workspace.read('trails_osm.json')) == 1


class TestOverpassRetry:
    """Overpass answers 429 as soon as its concurrent slots are full."""

    def response(self):
        class R:
            def read(self_inner):
                return b'{"elements": []}'

            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False
        return R()

    def test_retries_after_a_429(self, monkeypatch) -> None:
        attempts = {'n': 0}
        slept = []

        def fake_urlopen(req, timeout=None):
            attempts['n'] += 1
            if attempts['n'] < 3:
                raise urllib.error.HTTPError(
                    'u', 429, 'Too Many Requests', {}, None)
            return self.response()

        monkeypatch.setattr(bt.urllib.request, 'urlopen', fake_urlopen)
        result = bt.overpass('T', 'A', sleep=slept.append)

        assert result == {'elements': []}
        assert attempts['n'] == 3
        # Backoff widens rather than retrying at a fixed interval.
        assert slept == [bt.RETRY_BACKOFF, bt.RETRY_BACKOFF * 2]

    def test_retries_a_504(self, monkeypatch) -> None:
        attempts = {'n': 0}

        def fake_urlopen(req, timeout=None):
            attempts['n'] += 1
            if attempts['n'] == 1:
                raise urllib.error.HTTPError('u', 504, 'Gateway Timeout', {}, None)
            return self.response()

        monkeypatch.setattr(bt.urllib.request, 'urlopen', fake_urlopen)
        bt.overpass('T', 'A', sleep=lambda s: None)
        assert attempts['n'] == 2

    def test_gives_up_after_the_last_attempt(self, monkeypatch) -> None:
        def always_busy(req, timeout=None):
            raise urllib.error.HTTPError('u', 429, 'Too Many Requests', {}, None)

        monkeypatch.setattr(bt.urllib.request, 'urlopen', always_busy)
        with pytest.raises(urllib.error.HTTPError):
            bt.overpass('T', 'A', sleep=lambda s: None)

    def test_other_errors_are_not_retried(self, monkeypatch) -> None:
        """A 400 is a broken query; retrying it just wastes someone's server."""
        attempts = {'n': 0}

        def bad_request(req, timeout=None):
            attempts['n'] += 1
            raise urllib.error.HTTPError('u', 400, 'Bad Request', {}, None)

        monkeypatch.setattr(bt.urllib.request, 'urlopen', bad_request)
        with pytest.raises(urllib.error.HTTPError):
            bt.overpass('T', 'A', sleep=lambda s: None)
        assert attempts['n'] == 1
