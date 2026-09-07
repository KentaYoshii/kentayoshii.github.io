"""Unit tests for the title/author normalisers in scripts/merge_books.py.

These lock down the matching drift the README describes: the Goodreads export
and the hand-written log spell the same book differently, and the normalisers
are what bridge the two. A regression here is silent — a book simply stops
matching, loses its ISBN, and shows no cover — so the awkward cases are
pinned individually rather than through the end-to-end merge alone.
"""

import pytest

import merge_books as mb


class TestKeyify:
    """keyify() is the match key both sides are reduced to."""

    @pytest.mark.parametrize('left, right', [
        # Latin diacritics fold away, so the two spellings of a romanised
        # Japanese name meet.
        ('Shōgun', 'Shogun'),
        ('Brontë', 'Bronte'),
        ('Natsume Sōseki', 'Natsume Soseki'),
        # NFKC pulls full-width characters down to ASCII.
        ('１Ｑ８４', '1Q84'),
        ('Ｊｏｈｎ Ｇｒｅｅｎ', 'John Green'),
        # Case, spacing and punctuation are all dropped.
        ('King rat', 'King Rat'),
        ('Moby-Dick', 'moby dick'),
        ("Winesburg, Ohio", 'Winesburg Ohio'),
    ])
    def test_variants_share_a_key(self, left: str, right: str) -> None:
        """Spellings that mean the same book collapse onto one key."""
        assert mb.keyify(left) == mb.keyify(right)

    def test_japanese_voiced_marks_are_preserved(self) -> None:
        """が must not fold into か.

        fold() strips combining marks to handle Latin accents; the dakuten and
        handakuten are combining marks too, and stripping them would merge
        unrelated Japanese titles.
        """
        assert mb.keyify('が') != mb.keyify('か')
        assert mb.keyify('パ') != mb.keyify('ハ')

    def test_cjk_survives(self) -> None:
        """A Japanese title must not reduce to an empty key."""
        assert mb.keyify('永遠の0') == '永遠の0'
        assert mb.keyify('同志少女よ、敵を撃て') == '同志少女よ敵を撃て'

    def test_punctuation_only_input_is_empty(self) -> None:
        assert mb.keyify('--- ,;: ---') == ''


class TestStripSeries:
    """Goodreads annotates titles; the log does not."""

    @pytest.mark.parametrize('raw, expected', [
        ('1Q84 (1Q84, #1-3)', '1Q84'),
        ('The Abduction (Theodore Boone, #2)', 'The Abduction'),
        ('君のクイズ (Japanese Edition)', '君のクイズ'),
        # Romanisation is bracketed rather than parenthesised.
        ('永遠の0 [Eien No Zero]', '永遠の0'),
    ])
    def test_trailing_annotation_is_dropped(self, raw: str, expected: str) -> None:
        assert mb.strip_series(raw) == expected

    def test_subtitle_is_kept(self) -> None:
        """A colon subtitle is not an annotation — title_keys handles it."""
        title = 'Sapiens: A Brief History of Humankind'
        assert mb.strip_series(title) == title

    def test_only_a_trailing_group_is_dropped(self) -> None:
        """A parenthetical mid-title is part of the title."""
        assert mb.strip_series('The (Honest) Truth') == 'The (Honest) Truth'


class TestParseSeries:
    """The '#' is what separates a series tag from any other parenthetical."""

    def test_series_with_index(self) -> None:
        name, index = mb.parse_series(
            'The Return of Sherlock Holmes (Sherlock Holmes, #6)')
        assert (name, index) == ('Sherlock Holmes', '6')

    def test_omnibus_keeps_its_range(self) -> None:
        assert mb.parse_series('1Q84 (1Q84, #1-3)') == ('1Q84', '1-3')

    @pytest.mark.parametrize('title', [
        '君のクイズ (Japanese Edition)',
        'The Fall (Vintage International)',
        'Plain Title',
    ])
    def test_plain_parenthetical_is_not_a_series(self, title: str) -> None:
        """No '#', so this is an edition note, not a series position."""
        assert mb.parse_series(title) == (None, None)


class TestTitleKeys:
    """title_keys() emits every form a title might be matched under."""

    def test_subtitle_bridges_to_short_form(self) -> None:
        """Goodreads keeps the subtitle; the log writes 'Sapiens'."""
        long_keys = mb.title_keys('Sapiens: A Brief History of Humankind')
        assert mb.keyify('Sapiens') in long_keys

    def test_semicolon_subtitle_bridges_too(self) -> None:
        assert mb.keyify('Moby-Dick') in mb.title_keys('Moby-Dick; or, The Whale')

    def test_series_prefix_bridges_in_reverse(self) -> None:
        """The log writes 'Theodore Boone: The Abduction'; Goodreads files it
        as 'The Abduction (Theodore Boone, #2)'. The two must share a key."""
        log_keys = set(mb.title_keys('Theodore Boone: The Abduction'))
        goodreads_keys = set(mb.title_keys('The Abduction (Theodore Boone, #2)'))
        assert log_keys & goodreads_keys

    def test_part_suffix_is_stripped(self) -> None:
        """One novel read in two sittings still matches the single work."""
        assert mb.title_keys('Shogun Part 1') == mb.title_keys('Shogun')
        assert mb.title_keys('Shogun Part Two') == mb.title_keys('Shogun')

    def test_collection_catch_all_bridges(self) -> None:
        """Goodreads names a collection after its lead story plus a catch-all."""
        long_keys = set(mb.title_keys('The Dancing Girl of Izu and Other Stories'))
        short_keys = set(mb.title_keys('The Dancing Girl of Izu'))
        assert short_keys <= long_keys

    def test_leading_article_is_indexed_both_ways(self) -> None:
        keys = mb.title_keys('The Covenant of Water')
        assert mb.keyify('covenant of water') in keys
        assert mb.keyify('the covenant of water') in keys

    def test_keys_are_sorted_for_determinism(self) -> None:
        """Returned sorted, not as a set: an entry can match several records,
        and which one wins must not depend on the hash seed, or the generated
        file churns between runs."""
        keys = mb.title_keys('Sapiens: A Brief History of Humankind')
        assert keys == sorted(keys)

    def test_annotation_only_title_yields_no_key(self) -> None:
        assert mb.title_keys('(Boxed Set)') == []


class TestAliases:
    """Pairs the normaliser cannot bridge, listed explicitly in ALIASES."""

    def test_alias_produces_the_goodreads_key(self) -> None:
        keys = mb.alias_keys('The Strange Case of Dr. Jekyll and Mr. Hyde')
        assert mb.keyify('Dr. Jekyll and Mr. Hyde') in keys

    def test_alias_bridges_a_split_volume(self) -> None:
        assert mb.keyify('俺たちの箱根駅伝 上') in mb.alias_keys('俺たちの箱根駅伝')

    def test_unaliased_title_adds_nothing(self) -> None:
        assert mb.alias_keys('Some Book Nobody Aliased') == []

    def test_every_alias_target_is_reachable(self) -> None:
        """A typo on either side of ALIASES would silently do nothing."""
        for source, target in mb.ALIASES.items():
            assert mb.title_keys(target), 'alias target yields no key: %r' % target
            assert set(mb.alias_keys(source)) >= set(mb.title_keys(target))


class TestSortTitleAndLetter:
    """The A-Z list files titles under their first significant word."""

    @pytest.mark.parametrize('title, expected', [
        ('The Covenant of Water', 'Covenant of Water'),
        ('An Artist of the Floating World', 'Artist of the Floating World'),
        ('A Tale of Two Cities', 'Tale of Two Cities'),
        ('Theodore Boone', 'Theodore Boone'),  # 'The' only as a whole word
    ])
    def test_leading_article_is_dropped(self, title: str, expected: str) -> None:
        assert mb.sort_title(title) == expected

    @pytest.mark.parametrize('title, expected', [
        ('The Covenant of Water', 'C'),
        ('Shōgun', 'S'),          # accent folded before bucketing
        ('1984', '#'),            # digits collect under '#'
        ('永遠の0', '#'),           # so does anything non-Latin
    ])
    def test_letter_bucket(self, title: str, expected: str) -> None:
        assert mb.letter_of(title) == expected

    def test_empty_title_buckets_under_hash(self) -> None:
        assert mb.letter_of('') == '#'


class TestCsvFieldParsing:
    """Goodreads' CSV quirks."""

    @pytest.mark.parametrize('raw, expected', [
        ('="0525555366"', '0525555366'),   # wrapped for Excel
        ('0525555366', '0525555366'),      # ...and sometimes not
        ('=""', ''),                       # the empty-ISBN form
        ('  ="123"  ', '123'),
        ('', ''),
        (None, ''),
    ])
    def test_clean_excel(self, raw, expected: str) -> None:
        assert mb.clean_excel(raw) == expected

    @pytest.mark.parametrize('raw, expected', [
        ('368', 368),
        ('368.0', 368),      # page counts arrive as floats
        ('-750', -750),      # BC publication years
        ('', None),
        ('abc', None),
        (None, None),
    ])
    def test_as_int(self, raw, expected) -> None:
        assert mb.as_int(raw) == expected

    def test_squash_collapses_doubled_spaces(self) -> None:
        assert mb.squash('John  Green') == 'John Green'
        assert mb.squash('  a  b  ') == 'a b'
