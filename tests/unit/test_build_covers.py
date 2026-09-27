"""Unit tests for scripts/build_covers.py.

The parts worth pinning are the offline ones: the title parsing that decides
what TMDB gets asked, and apply_covers(), which must be a pure function of the
committed cache. If it ever reached the network, CI's byte-comparison of
docs/_data would start failing on a machine with different connectivity.

Nothing here makes a request; the network paths are covered in the integration
test with a stubbed opener.
"""

import pytest

import build_covers as bc


class TestParseMovieTitle:
    """Log titles carry annotations that must not reach TMDB as search text."""

    def test_plain_title_is_unchanged(self) -> None:
        info = bc.parse_movie_title('Dune')
        assert info == {'title': 'Dune', 'is_series': False, 'year': None}

    @pytest.mark.parametrize('raw, title', [
        ('Reacher Season 2 (TV Series)', 'Reacher'),
        ('Fallout (TV Series)', 'Fallout'),
        ('Reacher Season 2', 'Reacher'),
    ])
    def test_series_markers_are_stripped_and_flagged(self, raw: str, title: str) -> None:
        info = bc.parse_movie_title(raw)
        assert info['title'] == title
        assert info['is_series'] is True

    @pytest.mark.parametrize('raw, year', [
        ('Blade (1998)', '1998'),
        ('Kingdom of the Planet of the Apes (2024)', '2024'),
        # The Wikipedia-style disambiguator, which the browser-side version
        # could not parse and so searched for literally.
        ('The Count of Monte-Cristo (2024 film)', '2024'),
        ('Nosferatu (1922 Film)', '1922'),
    ])
    def test_trailing_year_becomes_a_filter(self, raw: str, year: str) -> None:
        info = bc.parse_movie_title(raw)
        assert info['year'] == year
        assert '(' not in info['title']

    def test_a_year_inside_the_title_is_kept(self) -> None:
        """'2012' is the film's name, not a release-year annotation."""
        assert bc.parse_movie_title('2012')['title'] == '2012'

    def test_a_non_year_parenthetical_is_left_alone(self) -> None:
        """Only years and series markers are annotations; anything else is
        part of the title and TMDB should see it."""
        info = bc.parse_movie_title('Peter Pan (Live Action)')
        assert info['title'] == 'Peter Pan (Live Action)'
        assert info['year'] is None

    def test_empty_input(self) -> None:
        assert bc.parse_movie_title('') is None
        assert bc.parse_movie_title(None) is None


class TestKeys:
    def test_book_key_is_case_insensitive(self) -> None:
        a = bc.book_key({'title': 'Kokoro', 'author': 'Natsume Soseki'})
        b = bc.book_key({'title': 'kokoro', 'author': 'NATSUME SOSEKI'})
        assert a == b

    def test_book_key_separates_same_title_by_author(self) -> None:
        a = bc.book_key({'title': 'Persuasion', 'author': 'Jane Austen'})
        b = bc.book_key({'title': 'Persuasion', 'author': 'Someone Else'})
        assert a != b

    def test_book_key_tolerates_a_missing_author(self) -> None:
        assert bc.book_key({'title': 'Untitled', 'author': None})

    def test_movie_key_is_the_lowercased_title(self) -> None:
        """Annotations stay in the key: 'Kingdom (2024)' and 'Kingdom' are
        two log entries that may well want different posters."""
        assert bc.movie_key({'title': 'Dune'}) == 'dune'
        assert bc.movie_key({'title': 'Blade (1998)'}) != bc.movie_key({'title': 'Blade'})


class TestApplyCovers:
    """apply_covers() is the offline pass build.py and CI depend on."""

    def test_isbn_becomes_a_url_without_a_cache_entry(self) -> None:
        books = [{'title': 'T', 'author': 'A', 'isbn': '9780062316097'}]
        cache = {'books': {}, 'movies': {}}
        bc.apply_covers(books, [], cache)
        assert books[0]['cover'] == (
            'https://covers.openlibrary.org/b/isbn/9780062316097-M.jpg?default=false')

    def test_isbn_is_url_quoted(self) -> None:
        """A stray space in the export must not produce a broken URL."""
        books = [{'title': 'T', 'author': 'A', 'isbn': '978 0062316097'}]
        bc.apply_covers(books, [], {'books': {}, 'movies': {}})
        assert ' ' not in books[0]['cover']

    def test_isbn_less_book_reads_the_cache(self) -> None:
        books = [{'title': 'Handwritten', 'author': 'A A', 'isbn': ''}]
        cache = {'books': {'handwritten|a a': 'https://example.test/x.jpg'},
                 'movies': {}}
        bc.apply_covers(books, [], cache)
        assert books[0]['cover'] == 'https://example.test/x.jpg'

    def test_uncached_book_gets_an_explicit_null(self) -> None:
        """The template tests for a cover, so the key has to exist."""
        books = [{'title': 'Unknown', 'author': 'A A', 'isbn': ''}]
        bc.apply_covers(books, [], {'books': {}, 'movies': {}})
        assert books[0]['cover'] is None

    def test_a_cached_miss_stays_a_miss(self) -> None:
        """null in the cache means 'looked it up, there is nothing'."""
        books = [{'title': 'Unknown', 'author': 'A A', 'isbn': ''}]
        cache = {'books': {'unknown|a a': None}, 'movies': {}}
        bc.apply_covers(books, [], cache)
        assert books[0]['cover'] is None

    def test_movies_read_the_cache(self) -> None:
        movies = [{'title': 'Dune'}, {'title': 'Nothing Here'}]
        cache = {'books': {}, 'movies': {'dune': 'https://example.test/d.jpg'}}
        bc.apply_covers(movies=movies, books=[], cache=cache)
        assert movies[0]['cover'] == 'https://example.test/d.jpg'
        assert movies[1]['cover'] is None

    def test_counts_are_reported(self) -> None:
        books = [
            {'title': 'A', 'author': 'X', 'isbn': '111'},
            {'title': 'B', 'author': 'X', 'isbn': '', },
            {'title': 'C', 'author': 'X', 'isbn': ''},
        ]
        cache = {'books': {'b|x': 'https://example.test/b.jpg'},
                 'movies': {'m': None}}
        counts = bc.apply_covers(books, [{'title': 'M'}], cache)
        assert counts['book_isbn'] == 1
        assert counts['book_search'] == 1
        assert counts['book_missing'] == 1
        assert counts['movie_missing'] == 1

    def test_is_idempotent(self) -> None:
        """Running the build twice must not change the output, or CI's
        byte-comparison of docs/_data fails on every second run."""
        def fresh():
            return ([{'title': 'A', 'author': 'X', 'isbn': '111'},
                     {'title': 'B', 'author': 'X', 'isbn': ''}],
                    [{'title': 'M'}])

        cache = {'books': {'b|x': 'https://example.test/b.jpg'},
                 'movies': {'m': 'https://example.test/m.jpg'}}

        books, movies = fresh()
        bc.apply_covers(books, movies, cache)
        first = (books, movies)

        books, movies = fresh()
        bc.apply_covers(books, movies, cache)
        bc.apply_covers(books, movies, cache)
        assert (books, movies) == first


class TestWantedKeys:
    def test_isbn_books_need_no_cache_entry(self) -> None:
        books = [{'title': 'A', 'author': 'X', 'isbn': '111'},
                 {'title': 'B', 'author': 'X', 'isbn': ''}]
        keep_books, _ = bc.wanted_keys(books, [])
        assert keep_books == {'b|x'}

    def test_every_movie_needs_one(self) -> None:
        _, keep_movies = bc.wanted_keys([], [{'title': 'Dune'}, {'title': 'Heat'}])
        assert keep_movies == {'dune', 'heat'}
