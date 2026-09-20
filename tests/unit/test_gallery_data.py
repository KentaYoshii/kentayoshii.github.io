"""Unit tests for scripts/gallery_data.py.

gallery.yml is parsed here by a deliberately small hand-written reader rather
than by PyYAML, and read by Jekyll's real parser on the other side. The risk
that buys is a silent disagreement between the two — a line one accepts and
the other drops — so the tests below pin the subset and check that anything
outside it fails loudly instead of quietly losing a photo.
"""

import pytest

import gallery_data as gd


class TestParseValue:
    @pytest.mark.parametrize('raw, value', [
        (' Zion', 'Zion'),
        ('Wyoming / Montana / Idaho', 'Wyoming / Montana / Idaho'),
        ('  Hawaiʻi Volcanoes  ', 'Hawaiʻi Volcanoes'),
        ('2025-10-02', '2025-10-02'),
    ])
    def test_scalars_are_stripped_strings(self, raw: str, value: str) -> None:
        assert gd.parse_value(raw) == value

    @pytest.mark.parametrize('raw', ['', '   ', '\t'])
    def test_empty_is_none(self, raw: str) -> None:
        assert gd.parse_value(raw) is None

    @pytest.mark.parametrize('raw, value', [
        ('[canyon, water]', ['canyon', 'water']),
        ('[ canyon ,water ]', ['canyon', 'water']),
        ('[solo]', ['solo']),
        ('[]', []),
        ('[a, , b]', ['a', 'b']),
        ('["a", \'b\']', ['a', 'b']),
    ])
    def test_inline_lists(self, raw: str, value: list) -> None:
        assert gd.parse_value(raw) == value

    @pytest.mark.parametrize('raw, value', [
        ('"2025-10-02"', '2025-10-02'),
        ("'Utah'", 'Utah'),
        ('"quoted"', 'quoted'),
    ])
    def test_surrounding_quotes_are_stripped(self, raw: str, value: str) -> None:
        # Dates are written quoted so a real YAML parser returns a string
        # rather than a date object. Leaving the quote characters in would
        # put them on the page.
        assert gd.parse_value(raw) == value

    @pytest.mark.parametrize('raw', [
        'The Narrows, "looking upstream"',
        '"mismatched\'',
        'a "quote" inside',
    ])
    def test_quotes_that_do_not_wrap_the_value_are_kept(self, raw: str) -> None:
        assert gd.parse_value(raw) == raw


class TestParseGallery:
    def test_reads_a_sequence_of_mappings(self) -> None:
        records = gd.parse_gallery(
            '- image: /assets/gallery/a.jpeg\n'
            '  park: Zion\n'
            '  location: Utah\n'
            '- image: /assets/gallery/b.jpeg\n'
            '  park: Olympic\n'
        )
        assert records == [
            {'image': '/assets/gallery/a.jpeg', 'park': 'Zion',
             'location': 'Utah'},
            {'image': '/assets/gallery/b.jpeg', 'park': 'Olympic'},
        ]

    def test_comments_and_blank_lines_are_skipped(self) -> None:
        records = gd.parse_gallery(
            '# a leading note\n'
            '\n'
            '- image: /assets/gallery/a.jpeg\n'
            '   # indented comment\n'
            '  park: Zion\n'
            '\n'
        )
        assert records == [{'image': '/assets/gallery/a.jpeg', 'park': 'Zion'}]

    def test_file_order_is_preserved(self) -> None:
        source = ''.join('- image: /assets/gallery/%d.jpeg\n' % n
                         for n in range(5))
        images = [r['image'] for r in gd.parse_gallery(source)]
        assert images == ['/assets/gallery/%d.jpeg' % n for n in range(5)]

    def test_a_value_may_contain_a_colon(self) -> None:
        records = gd.parse_gallery('- caption: Sunrise: the first light\n')
        assert records[0]['caption'] == 'Sunrise: the first light'

    def test_empty_source_is_no_records(self) -> None:
        assert gd.parse_gallery('') == []

    def test_key_before_any_item_is_an_error(self) -> None:
        with pytest.raises(gd.GalleryError):
            gd.parse_gallery('  park: Zion\n')

    def test_missing_separator_is_an_error(self) -> None:
        with pytest.raises(gd.GalleryError):
            gd.parse_gallery('- image: /a.jpeg\n  just some prose\n')

    def test_unindented_continuation_is_an_error(self) -> None:
        with pytest.raises(gd.GalleryError):
            gd.parse_gallery('- image: /a.jpeg\npark: Zion\n')


class TestAgreesWithRealYaml:
    """The check that actually matters.

    Jekyll reads gallery.yml with a real YAML parser and this repo reads it
    with the small one in gallery_data. A disagreement between them would show
    up as a photo silently missing from the page, or present with a field the
    generator never saw. PyYAML is not a dependency of this repo and CI does
    not install it, so this skips where it is absent and guards where it is
    not -- which is the machine the file is actually edited on.
    """

    def test_the_committed_file_parses_identically(self) -> None:
        yaml = pytest.importorskip('yaml')

        with open(gd.GALLERY_YML, encoding='utf-8') as handle:
            source = handle.read()

        assert gd.parse_gallery(source) == yaml.safe_load(source)

    def test_the_documented_shape_parses_identically(self) -> None:
        yaml = pytest.importorskip('yaml')

        source = (
            '# a comment\n'
            '- image: /assets/gallery/zion_1.jpeg\n'
            '  park: Zion\n'
            '  location: Utah\n'
            '  caption: The Narrows, looking upstream\n'
            '  date: 2025-10-02\n'
            '  tags: [canyon, water]\n'
            '- image: /assets/gallery/a.jpeg\n'
            '  location: Wyoming / Montana / Idaho\n'
        )
        mine = gd.parse_gallery(source)
        theirs = yaml.safe_load(source)
        # date is the one type PyYAML coerces and this parser does not, so it
        # is compared as text. Nothing downstream does arithmetic on it.
        for record in theirs:
            if 'date' in record:
                record['date'] = str(record['date'])
        assert mine == theirs


class TestOriginalPath:
    def test_resolves_a_bare_filename_under_the_originals_directory(self) -> None:
        path = gd.original_path({'image': 'zion_1.jpeg'},
                                originals_dir='/tmp/originals')
        assert path == '/tmp/originals/zion_1.jpeg'

    def test_tolerates_the_older_site_root_form(self) -> None:
        # `image` used to be a URL, back when the page served the original.
        path = gd.original_path({'image': '/assets/gallery/zion_1.jpeg'},
                                originals_dir='/tmp/originals')
        assert path == '/tmp/originals/zion_1.jpeg'

    def test_an_entry_without_an_image_is_an_error(self) -> None:
        with pytest.raises(gd.GalleryError):
            gd.original_path({'park': 'Zion'})

    def test_the_originals_live_outside_the_published_site(self) -> None:
        # The whole point of the move: docs/ is the Jekyll source, so anything
        # under it is published whether or not a page links to it.
        import os
        assert not gd.ORIGINALS_DIR.startswith(os.path.join(gd.ROOT, 'docs'))
