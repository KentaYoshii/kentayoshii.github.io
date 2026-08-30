#!/usr/bin/env python3
"""Generate the favicon and the Open Graph social card from the shelf data.

    python3 scripts/build_images.py

Both images are drawn from books.json rather than being static art, so the
social card is literally the shelf: one spine per book, width by page count,
colour by era. It changes as the shelf grows.

PNG is written by hand because this repo has no image library and the Space it
is developed in has neither Pillow nor ImageMagick. That is affordable only
because both images are axis-aligned rectangles -- no text is drawn, and none
is needed: link previews render og:title alongside the image, and a favicon at
32px has no room for words anyway.
"""

import json
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'docs', '_data')
OUT = os.path.join(ROOT, 'docs', 'assets')

CREAM = (0xFA, 0xF3, 0xE6)
# The same five era colours the Stats page uses for its spine wall.
ERAS = [
    (1800, (0x7D, 0x4A, 0x24)),
    (1900, (0xA8, 0x63, 0x2C)),
    (1950, (0xC0, 0x8A, 0x4B)),
    (2000, (0xD8, 0xA8, 0x6A)),
    (9999, (0xE8, 0xC9, 0x9A)),
]
UNKNOWN = (0xC8, 0xBA, 0xA6)

CARD_W, CARD_H = 1200, 630
CARD_ROWS = 6


def era_colour(published):
    if published is None:
        return UNKNOWN
    for cutoff, rgb in ERAS:
        if published < cutoff:
            return rgb
    return ERAS[-1][1]


class Canvas(object):
    """A flat RGB pixel buffer with one drawing primitive."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def rect(self, x, y, w, h, rgb):
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(self.w, int(x + w)), min(self.h, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(rgb) * (x1 - x0)
        for yy in range(y0, y1):
            start = (yy * self.w + x0) * 3
            self.px[start:start + len(row)] = row

    def write(self, path):
        def chunk(tag, data):
            return (struct.pack('>I', len(data)) + tag + data +
                    struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

        # Each scanline is prefixed with filter type 0 (None).
        stride = self.w * 3
        raw = bytearray()
        for y in range(self.h):
            raw.append(0)
            raw += self.px[y * stride:(y + 1) * stride]

        blob = b'\x89PNG\r\n\x1a\n'
        blob += chunk(b'IHDR', struct.pack('>IIBBBBB', self.w, self.h, 8, 2, 0, 0, 0))
        blob += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
        blob += chunk(b'IEND', b'')
        with open(path, 'wb') as f:
            f.write(blob)
        return len(blob)


def load_shelf():
    with open(os.path.join(DATA, 'books.json'), encoding='utf-8') as f:
        books = json.load(f)
    shelf = [b for b in books if b['pages']]
    shelf.sort(key=lambda b: (b['published'] is None, b['published'] or 0))
    return shelf


def draw_card(shelf):
    """The whole shelf, oldest first, wrapped into rows."""
    c = Canvas(CARD_W, CARD_H, CREAM)
    pad, gap = 56, 16
    usable = CARD_W - pad * 2
    total = sum(b['pages'] for b in shelf)
    # Pick the scale that makes the spines fill exactly CARD_ROWS rows. The
    # +1px per spine accounts for the gap each one carries.
    scale = total / float(usable * CARD_ROWS - len(shelf))
    row_h = 74

    block_h = CARD_ROWS * row_h + (CARD_ROWS - 1) * gap
    y = (CARD_H - block_h) // 2
    x = pad
    row = 0
    for b in shelf:
        w = max(2, int(b['pages'] / scale))
        if x + w > CARD_W - pad:
            row += 1
            if row >= CARD_ROWS:
                break
            x = pad
            y += row_h + gap
        # Books on a shelf are not all the same height. Vary the top edge by a
        # deterministic amount so the rows read as spines rather than as bars.
        h = row_h - (b['pages'] * 7 + len(b['title'])) % 13
        c.rect(x, y + (row_h - h), w, h, era_colour(b['published']))
        x += w + 1
    return c


def draw_favicon(size):
    """A handful of spines, sized to read at 16px."""
    c = Canvas(size, size, CREAM)
    unit = size / 16.0
    # width, height (in 16ths), colour index
    spines = [(3, 11, 0), (2, 13, 1), (3, 9, 2), (2, 12, 3), (3, 10, 1)]
    x = unit
    for w, h, idx in spines:
        pw, ph = w * unit, h * unit
        c.rect(x, size - unit - ph, pw, ph, ERAS[idx][1])
        x += pw + max(1, unit * 0.35)
    # A baseline so the spines read as standing on a shelf.
    c.rect(0, size - unit, size, max(1, unit * 0.55), (0x5B, 0x4A, 0x3A))
    return c


def main():
    shelf = load_shelf()
    os.makedirs(OUT, exist_ok=True)

    jobs = [
        ('social-card.png', draw_card(shelf)),
        ('favicon.png', draw_favicon(64)),
        ('apple-touch-icon.png', draw_favicon(180)),
    ]
    for name, canvas in jobs:
        n = canvas.write(os.path.join(OUT, name))
        print('wrote %-22s %4dx%-4d %6.1f KB'
              % ('assets/' + name, canvas.w, canvas.h, n / 1024.0))
    print('  card drawn from %d books, %s pages'
          % (len(shelf), '{:,}'.format(sum(b['pages'] for b in shelf))))


if __name__ == '__main__':
    main()
