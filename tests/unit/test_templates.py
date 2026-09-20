"""Static checks on the Jekyll templates.

There is no Ruby in the usual development Space, so `jekyll build` cannot be
run locally and the first real render is CI's `site` job. That job only fails
on a Liquid *syntax* error, though; a template can be perfectly valid Liquid
and still emit broken HTML. These checks cover the two ways that has actually
happened, both of which produced a clean build and a wrong page.
"""

import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, 'docs')

# Matches an HTML start tag, allowing newlines inside it but not nesting.
START_TAG = re.compile(r'<[a-zA-Z][^<>]*?>', re.S)

LIQUID_BLOCKS = {
    'for': 'endfor',
    'if': 'endif',
    'unless': 'endunless',
    'comment': 'endcomment',
    'case': 'endcase',
    'capture': 'endcapture',
    'raw': 'endraw',
    'tablerow': 'endtablerow',
}


def templates():
    found = []
    for directory, _, names in os.walk(DOCS):
        if os.sep + '_site' in directory:
            continue
        for name in names:
            if name.endswith(('.markdown', '.html')):
                found.append(os.path.join(directory, name))
    return sorted(found)


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


@pytest.mark.parametrize('path', templates(), ids=lambda p: os.path.relpath(p, ROOT))
class TestTemplate:
    def test_no_whitespace_stripping_inside_an_html_tag(self, path: str) -> None:
        """Liquid's {%- -%} must not appear between HTML attributes.

        It strips the newline and indentation on both sides, so the attributes
        either side end up touching:

            data-park="Olympic"data-when="26 July 2026"

        Kramdown's HTML parser requires whitespace before every attribute
        name. Faced with that it does not raise -- it abandons the start tag
        and escapes it, so the page displays the raw markup as text while the
        elements nested inside it still render. The build succeeds and CI
        stays green.
        """
        offenders = []
        source = read(path)
        for match in START_TAG.finditer(source):
            tag = match.group(0)
            if '{%-' in tag or '-%}' in tag:
                line = source[:match.start()].count('\n') + 1
                offenders.append('line %d: %s' % (line, ' '.join(tag.split())[:100]))
        assert not offenders, (
            'Liquid whitespace stripping inside an HTML tag in %s:\n  %s\n'
            'Move the tag out of the attribute list, or drop the "-".'
            % (os.path.relpath(path, ROOT), '\n  '.join(offenders))
        )

    def test_every_liquid_tag_has_a_name(self, path: str) -> None:
        """No {% %} delimiter pair without a tag name in it.

        Liquid needs a word character for the tag name and raises a syntax
        error without one. It tokenises the inside of a comment block as well,
        so this bites even when the delimiter is only being quoted in prose to
        explain something -- which is exactly how it happened.

        The cost is high and the signal is low: Jekyll fails the build, and
        GitHub Pages responds by continuing to serve the previous version of
        the site. Nothing about the live page says it is stale.
        """
        source = read(path)
        offenders = []
        for match in re.finditer(r'\{%(.*?)%\}', source, re.S):
            body = match.group(1).strip().lstrip('-').strip()
            if not re.match(r'^\w+', body):
                line = source[:match.start()].count('\n') + 1
                offenders.append('line %d: %s' % (line, match.group(0)[:60]))
        assert not offenders, (
            'Liquid delimiters with no tag name in %s:\n  %s'
            % (os.path.relpath(path, ROOT), '\n  '.join(offenders))
        )

    def test_liquid_blocks_are_balanced(self, path: str) -> None:
        source = read(path)
        stack = []
        for match in re.finditer(r'\{%-?\s*(\w+)', source):
            name = match.group(1)
            if name in LIQUID_BLOCKS:
                stack.append((name, source[:match.start()].count('\n') + 1))
            elif name in LIQUID_BLOCKS.values():
                opener = next(k for k, v in LIQUID_BLOCKS.items() if v == name)
                assert stack, '%s: stray {%% %s %%}' % (path, name)
                assert stack[-1][0] == opener, (
                    '%s: {%% %s %%} on line %d closed by {%% %s %%}'
                    % (path, stack[-1][0], stack[-1][1], name))
                stack.pop()
        assert not stack, '%s: unclosed %r' % (path, stack)


class TestParksTemplate:
    """Checks specific to /adventure/parks/, where the photographs live."""

    def path(self):
        return os.path.join(DOCS, 'adventure', 'parks.markdown')

    def test_the_grid_serves_derivatives_and_never_an_original(self) -> None:
        source = read(self.path())
        emitted = re.findall(r"'(/assets/gallery/[^']*)'", source)
        assert emitted, 'expected the template to build derivative URLs'
        for url in emitted:
            assert url.startswith(('/assets/gallery/thumbs/',
                                   '/assets/gallery/large/')), url

    def test_every_tile_attribute_the_script_reads_is_emitted(self) -> None:
        # Renaming an attribute in the template without changing main.js
        # breaks the lightbox silently -- getAttribute returns null and the
        # caption line just loses a field.
        source = read(self.path())
        js = read(os.path.join(DOCS, 'assets', 'js', 'main.js'))
        # Only reads off a photo tile. Scanning every getAttribute in the
        # file would also pick up the theme toggle and the books/movies list
        # sorting, which have nothing to do with this page.
        attributes = set(re.findall(r"tile\.getAttribute\('(data-[\w-]+)'\)", js))
        assert attributes, 'expected main.js to read tile attributes'
        for attribute in sorted(attributes):
            assert attribute + '=' in source, (
                '%s is read off a tile in main.js but never emitted by '
                'adventure/parks.markdown' % attribute)
