"""End-to-end tests for scripts/build_covers.py.

Covers the two things that would break the build if they regressed: the
offline pass must never touch the network (CI reruns it and byte-compares the
result), and a --fetch run that dies partway must not lose what it already
resolved.

get_json is stubbed throughout — no test here makes a real request.
"""

import json

import pytest

import build_covers as bc


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Point build_covers at a tmp docs/_data and return a helper to drive it."""
    data = tmp_path / '_data'
    data.mkdir()
    monkeypatch.setattr(bc, 'DATA', str(data))
    monkeypatch.setattr(bc, 'CACHE_PATH', str(data / 'covers.json'))
    # Keep the suite fast; nothing here is rate-limited.
    monkeypatch.setattr(bc, 'REQUEST_PAUSE', 0)

    class Workspace:
        path = data

        def write(self, books=None, movies=None, cache=None):
            (data / 'books.json').write_text(
                json.dumps(books or []), encoding='utf-8')
            (data / 'movies.json').write_text(
                json.dumps(movies or []), encoding='utf-8')
            if cache is not None:
                (data / 'covers.json').write_text(
                    json.dumps(cache), encoding='utf-8')

        def read(self, name):
            return json.loads((data / name).read_text(encoding='utf-8'))

        def run(self, *argv):
            return bc.main(list(argv))

    return Workspace()


@pytest.fixture
def no_network(monkeypatch):
    """Any request at all is a test failure."""
    def boom(url):
        raise AssertionError('unexpected network call: %s' % url)
    monkeypatch.setattr(bc, 'get_json', boom)


class TestOfflinePass:
    def test_makes_no_requests(self, workspace, no_network) -> None:
        workspace.write(
            books=[{'title': 'A', 'author': 'X', 'isbn': '9780062316097'},
                   {'title': 'B', 'author': 'X', 'isbn': ''}],
            movies=[{'title': 'Dune'}])
        assert workspace.run() == 0

    def test_writes_cover_onto_every_record(self, workspace, no_network) -> None:
        workspace.write(
            books=[{'title': 'A', 'author': 'X', 'isbn': '9780062316097'}],
            movies=[{'title': 'Dune'}],
            cache={'books': {}, 'movies': {'dune': 'https://example.test/d.jpg'}})
        workspace.run()
        assert 'covers.openlibrary.org' in workspace.read('books.json')[0]['cover']
        assert workspace.read('movies.json')[0]['cover'] == 'https://example.test/d.jpg'

    def test_is_byte_stable_across_runs(self, workspace, no_network) -> None:
        """This is what CI's `git diff --quiet -- docs/_data` relies on."""
        workspace.write(
            books=[{'title': 'A', 'author': 'X', 'isbn': '111'},
                   {'title': 'B', 'author': 'X', 'isbn': ''}],
            movies=[{'title': 'Dune'}, {'title': 'Heat'}],
            cache={'books': {'b|x': 'https://example.test/b.jpg'},
                   'movies': {'dune': 'https://example.test/d.jpg', 'heat': None}})
        workspace.run()
        snapshot = {n: (workspace.path / n).read_bytes()
                    for n in ('books.json', 'movies.json', 'covers.json')}
        workspace.run()
        workspace.run()
        for name, blob in snapshot.items():
            assert (workspace.path / name).read_bytes() == blob, name

    def test_prunes_entries_no_longer_referenced(self, workspace, no_network) -> None:
        workspace.write(
            books=[], movies=[{'title': 'Dune'}],
            cache={'books': {'gone|author': 'https://example.test/g.jpg'},
                   'movies': {'dune': None, 'retired': 'https://example.test/r.jpg'}})
        workspace.run()
        cache = workspace.read('covers.json')
        assert cache['books'] == {}
        assert set(cache['movies']) == {'dune'}

    def test_survives_a_missing_cache(self, workspace, no_network) -> None:
        workspace.write(books=[{'title': 'A', 'author': 'X', 'isbn': '111'}])
        assert workspace.run() == 0
        assert workspace.read('covers.json') == {'books': {}, 'movies': {}}

    def test_survives_a_corrupt_cache(self, workspace, no_network) -> None:
        """Derived data — a truncated file should rebuild, not crash."""
        workspace.write(books=[{'title': 'A', 'author': 'X', 'isbn': '111'}])
        (workspace.path / 'covers.json').write_text('{ oh no', encoding='utf-8')
        assert workspace.run() == 0


class TestFetchPass:
    def test_looks_up_only_what_is_missing(self, workspace, monkeypatch) -> None:
        asked = []

        def fake_get_json(url):
            asked.append(url)
            return {'results': [{'title': 'Heat', 'poster_path': '/h.jpg'}]}

        monkeypatch.setattr(bc, 'get_json', fake_get_json)
        monkeypatch.setenv('TMDB_API_KEY', 'test-key')
        workspace.write(
            movies=[{'title': 'Dune'}, {'title': 'Heat'}],
            cache={'books': {}, 'movies': {'dune': 'https://example.test/d.jpg'}})

        workspace.run('--fetch')

        # Dune was already cached, so only Heat is looked up.
        assert len(asked) == 1
        assert 'Heat' in asked[0]
        assert workspace.read('covers.json')['movies']['heat'] == \
            'https://image.tmdb.org/t/p/w200/h.jpg'

    def test_a_cached_null_is_not_retried(self, workspace, no_network) -> None:
        """null means 'asked, nothing there'; re-running must not ask again."""
        workspace.write(movies=[{'title': 'Obscure'}],
                        cache={'books': {}, 'movies': {'obscure': None}})
        assert workspace.run('--fetch') == 0

    def test_films_are_skipped_without_a_key(self, workspace, no_network,
                                             monkeypatch, capsys) -> None:
        monkeypatch.delenv('TMDB_API_KEY', raising=False)
        workspace.write(movies=[{'title': 'Dune'}])
        assert workspace.run('--fetch') == 0
        assert 'TMDB_API_KEY is not set' in capsys.readouterr().out

    def test_only_movies_leaves_books_alone(self, workspace, monkeypatch) -> None:
        """The escape hatch for when Open Library is unreachable."""
        def fake_get_json(url):
            assert 'openlibrary' not in url, 'books should not be fetched'
            return {'results': [{'title': 'Dune', 'poster_path': '/d.jpg'}]}

        monkeypatch.setattr(bc, 'get_json', fake_get_json)
        monkeypatch.setenv('TMDB_API_KEY', 'test-key')
        workspace.write(books=[{'title': 'No ISBN', 'author': 'X', 'isbn': ''}],
                        movies=[{'title': 'Dune'}])

        assert workspace.run('--fetch', '--only', 'movies') == 0
        cache = workspace.read('covers.json')
        assert cache['movies']['dune']
        assert cache['books'] == {}

    def test_a_network_failure_keeps_what_was_resolved(self, workspace,
                                                       monkeypatch) -> None:
        import urllib.error

        calls = {'n': 0}

        def flaky(url):
            calls['n'] += 1
            if calls['n'] == 1:
                return {'results': [{'title': 'First', 'poster_path': '/1.jpg'}]}
            raise urllib.error.URLError('connection reset')

        monkeypatch.setattr(bc, 'get_json', flaky)
        monkeypatch.setenv('TMDB_API_KEY', 'test-key')
        workspace.write(movies=[{'title': 'First'}, {'title': 'Second'}])

        assert workspace.run('--fetch') == 1
        cache = workspace.read('covers.json')
        assert cache['movies']['first'] == 'https://image.tmdb.org/t/p/w200/1.jpg'
        assert 'second' not in cache['movies']


class TestMovieSearchOrdering:
    def test_a_series_searches_tv_first(self, workspace, monkeypatch) -> None:
        """A film false-positive would otherwise win before TV is ever tried."""
        asked = []

        def fake_get_json(url):
            asked.append(url)
            return {'results': [{'name': 'Reacher', 'poster_path': '/r.jpg'}]}

        monkeypatch.setattr(bc, 'get_json', fake_get_json)
        info = bc.parse_movie_title('Reacher Season 2 (TV Series)')
        bc.fetch_movie_cover(info, 'test-key')
        assert '/search/tv' in asked[0]

    def test_a_film_searches_movies_first(self, workspace, monkeypatch) -> None:
        asked = []

        def fake_get_json(url):
            asked.append(url)
            return {'results': [{'title': 'Dune', 'poster_path': '/d.jpg'}]}

        monkeypatch.setattr(bc, 'get_json', fake_get_json)
        bc.fetch_movie_cover(bc.parse_movie_title('Dune'), 'test-key')
        assert '/search/movie' in asked[0]

    def test_an_exact_title_beats_a_more_popular_one(self, workspace,
                                                     monkeypatch) -> None:
        """TMDB ranks by popularity, so a short generic title can return an
        unrelated but busier film first."""
        def fake_get_json(url):
            return {'results': [
                {'title': 'Blade Runner', 'poster_path': '/wrong.jpg'},
                {'title': 'Blade', 'poster_path': '/right.jpg'},
            ]}

        monkeypatch.setattr(bc, 'get_json', fake_get_json)
        url = bc.fetch_movie_cover(bc.parse_movie_title('Blade'), 'test-key')
        assert url.endswith('/right.jpg')

    def test_results_without_a_poster_are_ignored(self, workspace, monkeypatch) -> None:
        def fake_get_json(url):
            return {'results': [{'title': 'Dune'}, {'title': 'Dune',
                                                    'poster_path': '/d.jpg'}]}

        monkeypatch.setattr(bc, 'get_json', fake_get_json)
        url = bc.fetch_movie_cover(bc.parse_movie_title('Dune'), 'test-key')
        assert url.endswith('/d.jpg')

    def test_the_release_year_is_passed_as_a_filter(self, workspace,
                                                    monkeypatch) -> None:
        asked = []

        def fake_get_json(url):
            asked.append(url)
            return {'results': [{'title': 'Blade', 'poster_path': '/b.jpg'}]}

        monkeypatch.setattr(bc, 'get_json', fake_get_json)
        bc.fetch_movie_cover(bc.parse_movie_title('Blade (1998)'), 'test-key')
        assert 'year=1998' in asked[0]
