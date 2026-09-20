#!/usr/bin/env python3
"""Read docs/_data/gallery.yml without a YAML dependency.

The rest of scripts/ is standard-library only so that build.py and CI can run
with nothing installed, and gallery.yml is the one data file the generators
read rather than write. Pulling in PyYAML for it would put an install step in
front of the whole build, so this parses the small subset of YAML the file
actually uses:

    - image: /assets/gallery/zion_1.jpeg
      caption: The Narrows, looking upstream
      date: 2025-10-02
      location: Utah
      park: Zion
      tags: [canyon, water]

That is: a flat sequence of mappings, scalar values, and one inline list. No
nesting, no anchors, no block scalars, no quoting. Anything outside that is a
syntax error here rather than something to support, since this file is
hand-edited against a documented shape (see the header of gallery.yml) and a
silent misparse would drop a photo from the page.

Jekyll still reads the same file with a real YAML parser, so the two must
agree on the subset. Keeping the subset this small is what makes that safe.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GALLERY_YML = os.path.join(ROOT, 'docs', '_data', 'gallery.yml')
GALLERY_DIR = os.path.join(ROOT, 'docs', 'assets', 'gallery')


class GalleryError(Exception):
    """A line in gallery.yml does not match the documented shape."""


def unquote(text):
    """Strip one matching pair of surrounding quotes, as YAML would.

    Dates are written quoted in gallery.yml so that a real YAML parser hands
    Jekyll a string rather than coercing them to a date object, which would
    make the two readers of this file disagree about the type.
    """
    if len(text) >= 2 and text[0] == text[-1] and text[0] in '"\'':
        return text[1:-1]
    return text


def parse_value(raw):
    """Turn the text after a ``key:`` into a string, a list, or None.

    An empty value is None rather than '' so a blank ``location:`` is absent
    rather than present-but-empty; the template tests for absence.
    """
    text = raw.strip()
    if not text:
        return None
    if text.startswith('[') and text.endswith(']'):
        inner = text[1:-1]
        return [unquote(part.strip()) for part in inner.split(',') if part.strip()]
    return unquote(text)


def parse_gallery(text):
    """Parse gallery.yml source into a list of dicts, in file order."""
    records = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        if stripped.startswith('- '):
            records.append({})
            stripped = stripped[2:]
        elif not line.startswith('  '):
            raise GalleryError(
                'line %d: expected a "- " item or a two-space indented key, '
                'got %r' % (number, line)
            )
        elif not records:
            raise GalleryError('line %d: key before the first "- " item' % number)

        if ':' not in stripped:
            raise GalleryError('line %d: no "key: value" separator in %r'
                               % (number, stripped))
        key, _, raw = stripped.partition(':')
        records[-1][key.strip()] = parse_value(raw)

    return records


def load_gallery(path=GALLERY_YML):
    """Parse gallery.yml from disk."""
    with open(path, encoding='utf-8') as handle:
        return parse_gallery(handle.read())


def original_path(entry, gallery_dir=GALLERY_DIR):
    """Absolute path of the committed original an entry points at.

    ``image`` is a site-root URL (/assets/gallery/x.jpeg); only the basename
    matters on disk.
    """
    image = entry.get('image')
    if not image:
        raise GalleryError('entry has no image: %r' % (entry,))
    return os.path.join(gallery_dir, os.path.basename(image))
