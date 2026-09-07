"""End-to-end tests for scripts/merge_books.py.

The merge decisions — which title wins, which author spelling wins, which year
is kept, when a series label survives — live in closures inside main(), so they
are exercised by running the whole thing against small fixture inputs rather
than by importing them.

Every test points CSV_PATH/LOG_PATH/OUT_PATH at a tmp_path, so none of this
touches the real export or docs/_data.
"""

import json
import os

import pytest

import merge_books as mb

# Only the columns merge_books reads. DictReader tolerates a narrower header
# than the real export, and listing 23 Goodreads columns would obscure which
# ones actually matter.
CSV_COLUMNS = [
    'Title', 'Author', 'ISBN', 'ISBN13', 'Number of Pages',
    'Year Published', 'Original Publication Year', 'Exclusive Shelf',
]


def write_csv(path, rows):
    """Write a Goodreads-shaped export. Each row is a dict of CSV_COLUMNS;
    anything omitted defaults to empty, and the shelf defaults to 'read'."""
    lines = [','.join(CSV_COLUMNS)]
    for row in rows:
        row = dict(row)
        row.setdefault('Exclusive Shelf', 'read')
        values = []
        for column in CSV_COLUMNS:
            value = str(row.get(column, ''))
            # Titles contain commas ('Winesburg, Ohio') and the ISBN columns
            # contain quotes, so quote everything and double any inner quote.
            values.append('"%s"' % value.replace('"', '""'))
        lines.append(','.join(values))
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def write_log(path, sections):
    """Write docs/_logs/books.md. `sections` maps a heading ('2024',
    'Undated') to a list of (title, author) pairs."""
    out = ['# Books', '']
    for heading, entries in sections.items():
        out.append('## %s' % heading)
        out.append('')
        for title, author in entries:
            out.append('- _%s_ by %s' % (title, author))
        out.append('')
    path.write_text('\n'.join(out), encoding='utf-8')


@pytest.fixture
def run_merge(tmp_path, monkeypatch):
    """Run merge_books.main() against fixture inputs; return the books written.

    Yields a callable so each test can supply its own rows and sections.
    """
    def run(csv_rows, log_sections=None):
        csv_path = tmp_path / 'goodreads_library_export.csv'
        log_path = tmp_path / 'books.md'
        out_path = tmp_path / '_data' / 'books.json'

        write_csv(csv_path, csv_rows)
        write_log(log_path, log_sections or {})

        monkeypatch.setattr(mb, 'CSV_PATH', str(csv_path))
        monkeypatch.setattr(mb, 'LOG_PATH', str(log_path))
        monkeypatch.setattr(mb, 'OUT_PATH', str(out_path))

        mb.main()

        with open(out_path, encoding='utf-8') as f:
            return json.load(f)

    return run


def by_title(books, title):
    """The one book with this exact output title."""
    hits = [b for b in books if b['title'] == title]
    assert len(hits) == 1, 'expected exactly one %r, got %r' % (
        title, [b['title'] for b in books])
    return hits[0]


class TestShelfFiltering:
    def test_only_the_read_shelf_is_used(self, run_merge) -> None:
        books = run_merge([
            {'Title': 'Finished', 'Author': 'A A', 'Exclusive Shelf': 'read'},
            {'Title': 'Someday', 'Author': 'B B', 'Exclusive Shelf': 'to-read'},
            {'Title': 'Halfway', 'Author': 'C C',
             'Exclusive Shelf': 'currently-reading'},
        ])
        assert [b['title'] for b in books] == ['Finished']


class TestTitleSelection:
    def test_log_short_title_wins(self, run_merge) -> None:
        """The log's curated short form beats Goodreads' subtitled one."""
        books = run_merge(
            [{'Title': 'Sapiens: A Brief History of Humankind',
              'Author': 'Yuval Noah Harari', 'ISBN13': '="9780062316097"'}],
            {'2024': [('Sapiens', 'Yuval Noah Harari')]},
        )
        book = by_title(books, 'Sapiens')
        # Matched, so it keeps the Goodreads ISBN and therefore its cover.
        assert book['isbn'] == '9780062316097'

    def test_goodreads_title_wins_when_parts_collapse(self, run_merge) -> None:
        """Two log rows for one work: neither label fits the merged entry."""
        books = run_merge(
            [{'Title': 'Shogun', 'Author': 'James Clavell'}],
            {'2024': [('Shogun Part 1', 'James Clavell'),
                      ('Shogun Part 2', 'James Clavell')]},
        )
        assert [b['title'] for b in books] == ['Shogun']

    def test_goodreads_title_wins_on_case_only_difference(self, run_merge) -> None:
        books = run_merge(
            [{'Title': 'King Rat', 'Author': 'James Clavell'}],
            {'2024': [('King rat', 'James Clavell')]},
        )
        assert [b['title'] for b in books] == ['King Rat']

    def test_unmatched_goodreads_book_keeps_its_own_title(self, run_merge) -> None:
        books = run_merge(
            [{'Title': 'Never Logged', 'Author': 'A A'}], {})
        assert [b['title'] for b in books] == ['Never Logged']


class TestAuthorCanonicalisation:
    def test_goodreads_spelling_wins_for_a_matched_book(self, run_merge) -> None:
        books = run_merge(
            [{'Title': 'Kokoro', 'Author': 'Natsume Sōseki'}],
            {'2024': [('Kokoro', 'Natsume Soseki')]},
        )
        assert books[0]['author'] == 'Natsume Sōseki'

    def test_log_only_book_adopts_the_goodreads_spelling(self, run_merge) -> None:
        """Otherwise one author splits into two sections on the page."""
        books = run_merge(
            [{'Title': 'The Hobbit', 'Author': 'J.R.R. Tolkien'}],
            {'2024': [('The Hobbit', 'J.R.R. Tolkien'),
                      ('The Silmarillion', 'J.R.R. Tolkien')]},
        )
        silmarillion = by_title(books, 'The Silmarillion')
        assert silmarillion['author'] == 'J.R.R. Tolkien'
        assert {b['author'] for b in books} == {'J.R.R. Tolkien'}


class TestYearSelection:
    def test_earliest_year_wins(self, run_merge) -> None:
        """A book logged twice keeps the first time it was read."""
        books = run_merge(
            [{'Title': 'Dune', 'Author': 'Frank Herbert'}],
            {'2025': [('Dune', 'Frank Herbert')],
             '2024': [('Dune', 'Frank Herbert')]},
        )
        assert books[0]['year'] == '2024'

    def test_undated_section_yields_no_year(self, run_merge) -> None:
        books = run_merge(
            [{'Title': 'Rashomon', 'Author': 'Ryunosuke Akutagawa'}],
            {'Undated': [('Rashomon', 'Ryunosuke Akutagawa')]},
        )
        assert books[0]['year'] is None

    def test_goodreads_only_book_has_no_year(self, run_merge) -> None:
        """The export's 'Date Read' column is empty throughout."""
        books = run_merge([{'Title': 'Unlogged', 'Author': 'A A'}], {})
        assert books[0]['year'] is None


class TestLogOnlyBooks:
    def test_log_only_book_has_no_goodreads_fields(self, run_merge) -> None:
        books = run_merge([], {'2024': [('Handwritten', 'A A')]})
        book = by_title(books, 'Handwritten')
        assert book['isbn'] == ''
        assert book['pages'] is None
        assert book['published'] is None
        assert book['series'] is None

    def test_duplicate_log_only_rows_collapse(self, run_merge) -> None:
        books = run_merge(
            [], {'2024': [('Twice Listed', 'A A')],
                 '2025': [('Twice Listed', 'A A')]})
        assert [b['title'] for b in books] == ['Twice Listed']


class TestSeries:
    def test_series_survives_once_enough_books_are_read(self, run_merge) -> None:
        books = run_merge([
            {'Title': 'A Study in Scarlet (Sherlock Holmes, #1)',
             'Author': 'Arthur Conan Doyle'},
            {'Title': 'The Sign of Four (Sherlock Holmes, #2)',
             'Author': 'Arthur Conan Doyle'},
        ])
        assert {b['series'] for b in books} == {'Sherlock Holmes'}
        assert by_title(books, 'The Sign of Four')['series_index'] == '2'

    def test_a_lone_series_book_drops_its_label(self, run_merge) -> None:
        """One book is not a series worth showing — it would just add a
        one-item section to the page."""
        books = run_merge([
            {'Title': 'A Study in Scarlet (Sherlock Holmes, #1)',
             'Author': 'Arthur Conan Doyle'},
        ])
        assert books[0]['series'] is None
        assert books[0]['series_index'] is None

    def test_edition_parenthetical_is_not_a_series(self, run_merge) -> None:
        books = run_merge([
            {'Title': 'The Fall (Vintage International)', 'Author': 'Albert Camus'},
            {'Title': 'The Plague (Vintage International)', 'Author': 'Albert Camus'},
        ])
        assert {b['series'] for b in books} == {None}


class TestGoodreadsFields:
    def test_isbn13_is_preferred_over_isbn(self, run_merge) -> None:
        books = run_merge([{'Title': 'T', 'Author': 'A A',
                            'ISBN': '="0525555366"',
                            'ISBN13': '="9780525555360"'}])
        assert books[0]['isbn'] == '9780525555360'

    def test_isbn10_is_the_fallback(self, run_merge) -> None:
        books = run_merge([{'Title': 'T', 'Author': 'A A',
                            'ISBN': '="0525555366"', 'ISBN13': '=""'}])
        assert books[0]['isbn'] == '0525555366'

    def test_original_publication_year_beats_this_edition(self, run_merge) -> None:
        """So the classics read as old rather than as their latest reprint."""
        books = run_merge([{'Title': 'Frankenstein', 'Author': 'Mary Shelley',
                            'Year Published': '2018',
                            'Original Publication Year': '1818'}])
        assert books[0]['published'] == 1818

    def test_edition_year_is_used_when_the_original_is_missing(self, run_merge) -> None:
        books = run_merge([{'Title': 'T', 'Author': 'A A',
                            'Year Published': '2011',
                            'Original Publication Year': ''}])
        assert books[0]['published'] == 2011

    def test_bc_publication_year_is_negative(self, run_merge) -> None:
        books = run_merge([{'Title': 'The Odyssey', 'Author': 'Homer',
                            'Original Publication Year': '-750'}])
        assert books[0]['published'] == -750


class TestOutputShape:
    def test_sorted_by_title_ignoring_leading_articles(self, run_merge) -> None:
        books = run_merge([
            {'Title': 'Zebra', 'Author': 'A A'},
            {'Title': 'The Covenant of Water', 'Author': 'B B'},
            {'Title': 'Anvil', 'Author': 'C C'},
        ])
        # 'The Covenant of Water' files under C, between Anvil and Zebra.
        assert [b['title'] for b in books] == [
            'Anvil', 'The Covenant of Water', 'Zebra']

    def test_letter_bucket_is_assigned(self, run_merge) -> None:
        books = run_merge([
            {'Title': 'The Covenant of Water', 'Author': 'A A'},
            {'Title': '1984', 'Author': 'George Orwell'},
        ])
        assert by_title(books, 'The Covenant of Water')['letter'] == 'C'
        assert by_title(books, '1984')['letter'] == '#'

    def test_every_book_has_the_full_key_set(self, run_merge) -> None:
        """The Liquid template reads each of these by name."""
        books = run_merge(
            [{'Title': 'Matched', 'Author': 'A A'}],
            {'2024': [('Matched', 'A A'), ('Log Only', 'B B')]},
        )
        expected = {'title', 'author', 'isbn', 'year', 'pages', 'published',
                    'series', 'series_index', 'letter'}
        for book in books:
            assert set(book) == expected

    def test_output_is_stable_across_runs(self, run_merge) -> None:
        """title_keys() returns sorted keys so the file does not churn between
        runs under different hash seeds."""
        rows = [
            {'Title': 'Sapiens: A Brief History of Humankind', 'Author': 'A A'},
            {'Title': 'Sapiens', 'Author': 'A A'},
        ]
        sections = {'2024': [('Sapiens', 'A A')]}
        assert run_merge(rows, sections) == run_merge(rows, sections)


class TestNearMissReport:
    def test_a_typo_is_reported(self, run_merge, capsys) -> None:
        """A misspelled log title costs the book its ISBN silently, so the
        script prints a suggestion instead."""
        run_merge(
            [{'Title': 'The Covenant of Water', 'Author': 'Abraham Verghese'}],
            {'2024': [('The Covenent of Water', 'Abraham Verghese')]},
        )
        out = capsys.readouterr().out
        assert 'look like an unmatched Goodreads book' in out
        assert 'The Covenant of Water' in out

    def test_a_different_author_is_not_reported(self, run_merge, capsys) -> None:
        """'Ford County' and 'Snow Country' trip the title test; the author
        check is what keeps the report quiet."""
        run_merge(
            [{'Title': 'Snow Country', 'Author': 'Yasunari Kawabata'}],
            {'2024': [('Ford County', 'John Grisham')]},
        )
        assert 'look like an unmatched Goodreads book' not in capsys.readouterr().out


class TestFileWriting:
    def test_output_directory_is_created(self, tmp_path, monkeypatch) -> None:
        """build.py may run before docs/_data exists on a fresh clone."""
        csv_path = tmp_path / 'export.csv'
        log_path = tmp_path / 'books.md'
        out_path = tmp_path / 'missing' / 'nested' / 'books.json'
        write_csv(csv_path, [{'Title': 'T', 'Author': 'A A'}])
        write_log(log_path, {})

        monkeypatch.setattr(mb, 'CSV_PATH', str(csv_path))
        monkeypatch.setattr(mb, 'LOG_PATH', str(log_path))
        monkeypatch.setattr(mb, 'OUT_PATH', str(out_path))
        mb.main()

        assert os.path.exists(out_path)

    def test_file_ends_with_a_newline(self, tmp_path, monkeypatch) -> None:
        """Otherwise every regeneration shows a no-newline-at-EOF diff."""
        csv_path = tmp_path / 'export.csv'
        log_path = tmp_path / 'books.md'
        out_path = tmp_path / 'books.json'
        write_csv(csv_path, [{'Title': 'T', 'Author': 'A A'}])
        write_log(log_path, {})

        monkeypatch.setattr(mb, 'CSV_PATH', str(csv_path))
        monkeypatch.setattr(mb, 'LOG_PATH', str(log_path))
        monkeypatch.setattr(mb, 'OUT_PATH', str(out_path))
        mb.main()

        assert out_path.read_text(encoding='utf-8').endswith('}\n]\n')
