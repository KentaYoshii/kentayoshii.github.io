#!/usr/bin/env python3
"""Generate the derivatives /gallery/ actually serves, from the originals.

    python3 scripts/build_gallery_thumbs.py
    python3 scripts/build_gallery_thumbs.py --force

The page used to serve the committed originals straight into the grid: 153 MB
across 36 photos, several over 6 MB, every one of them scaled down by the
browser into a box a few hundred pixels wide. `loading="lazy"` deferred the
cost but did not remove it. This writes two smaller copies of each photo and
the page serves those instead:

    assets/gallery/thumbs/  800 px wide   the grid tile
    assets/gallery/large/  2000 px wide   the lightbox

The originals stay committed and untouched as the source these are rebuilt
from; nothing links to them any more.

Also written is docs/_data/gallery_render.json, which carries the three things
the template cannot work out for itself:

  - the exact pixel size of every thumbnail, so the tiles can declare
    width/height and the grid stops reflowing as photos arrive;
  - a 16 px-wide copy of each photo inlined as a data URI, so a tile shows a
    blurred impression of its own photo immediately rather than a blank box;
  - a characteristic colour per photo and per park, which the page uses to
    tint each park's heading. Derived from the photographs rather than chosen.

Unlike the other generators this one needs Pillow, so it is deliberately NOT
part of build.py: that runs in CI with nothing installed and must stay
standard-library only. This is a manual pass run when photos are added, and
its output is committed -- the same arrangement as `build_covers.py --fetch`.
Pillow is imported inside main() so the module stays importable (and testable)
without it.
"""

import argparse
import base64
import colorsys
import io
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gallery_data  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GALLERY = os.path.join(ROOT, 'docs', 'assets', 'gallery')
DATA = os.path.join(ROOT, 'docs', '_data')

# Widths, not heights: the grid lays out in columns, and every photo here is
# landscape apart from one, so width is the dimension that bounds the work.
# 800 covers a ~300 px tile on a 2x display without paying for more.
SIZES = {'thumbs': 800, 'large': 2000}
QUALITY = {'thumbs': 80, 'large': 82}

# Wide enough to keep the shape of a scene, small enough that the whole set of
# 36 inlined placeholders costs less than a single photo used to.
LQIP_WIDTH = 16
LQIP_QUALITY = 40

# Colour extraction. A flat mean is the obvious approach and the wrong one:
# averaging a whole landscape converges on the same grey-blue for every park,
# because sky and rock dominate by area everywhere. Measured across these 36
# photos it put thirteen of the fourteen parks within a few percent of each
# other, which is useless as a way to tell them apart.
#
# So: quantise to a handful of clusters and pick the one that is both
# prominent and actually coloured, weighting by saturation. Two details earn
# their place --
#
#   - The top of the frame is dropped first. Sky is the most saturated thing
#     in most of these shots, so scoring on saturation picks it nearly every
#     time, and sky looks the same above every park. The ground is what
#     distinguishes them.
#   - Near-black and near-white clusters are skipped. A crushed shadow or a
#     blown highlight carries no hue worth reading.
SKY_CROP = 0.40
QUANT_COLOURS = 8
SATURATION_BIAS = 1.4
SAMPLE_BOX = (240, 240)

# Bounds the page's accent colours are pulled into, per theme, so a cave shot
# does not produce a heading too dark to read. Hue is never touched -- that is
# the part carrying which park this is. min_sat stays low deliberately: a park
# that genuinely photographs grey should stay grey rather than be handed an
# invented hue amplified out of sensor noise.
ACCENT_LIGHT = {'min_sat': 0.20, 'max_sat': 0.62, 'min_val': 0.30, 'max_val': 0.48}
ACCENT_DARK = {'min_sat': 0.18, 'max_sat': 0.55, 'min_val': 0.62, 'max_val': 0.80}


def scaled_size(size, target_width):
    """Fit (width, height) to target_width, preserving aspect, never upscaling.

    Returning the original size for an already-small photo matters: enlarging
    it would cost bytes to add no detail, and would make the declared
    width/height disagree with the file actually written.
    """
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError('bad image size: %r' % (size,))
    if width <= target_width:
        return width, height
    scaled_height = max(1, round(height * target_width / float(width)))
    return target_width, scaled_height


def derivative_path(original, kind, gallery_dir=GALLERY):
    """Where the `kind` copy of `original` belongs."""
    if kind not in SIZES:
        raise ValueError('unknown derivative: %r' % (kind,))
    return os.path.join(gallery_dir, kind, os.path.basename(original))


def is_stale(original, derivative):
    """True when the derivative is missing or older than its original."""
    if not os.path.exists(derivative):
        return True
    return os.path.getmtime(derivative) < os.path.getmtime(original)


def clamp(value, low, high):
    return max(low, min(high, value))


def to_hex(rgb):
    return '#%02x%02x%02x' % tuple(int(round(clamp(c, 0, 255))) for c in rgb)


def to_hsv(rgb):
    return colorsys.rgb_to_hsv(*[clamp(c, 0, 255) / 255.0 for c in rgb])


def combine_colours(colours):
    """Fold a park's per-photo colours into one.

    Averaging in RGB is wrong here: a park with an orange canyon and a blue
    lake averages to grey, which is a colour neither photo contains. Hue is an
    angle, so it is averaged as one -- weighted by saturation, so washed-out
    photos pull the result around less than vivid ones. Saturation and value
    are ordinary means.
    """
    if not colours:
        raise ValueError('no colours to combine')

    x = y = total_sat = total_val = 0.0
    for rgb in colours:
        hue, saturation, value = to_hsv(rgb)
        angle = hue * 2 * math.pi
        x += math.cos(angle) * saturation
        y += math.sin(angle) * saturation
        total_sat += saturation
        total_val += value

    count = float(len(colours))
    # With every photo fully desaturated the angle is undefined rather than
    # zero; hue is meaningless at that point anyway, so anchor it.
    hue = (math.atan2(y, x) / (2 * math.pi)) % 1.0 if total_sat > 1e-6 else 0.0
    rgb = colorsys.hsv_to_rgb(hue, total_sat / count, total_val / count)
    return tuple(c * 255 for c in rgb)


def accent(rgb, bounds):
    """Pull a colour into a range that reads against body text.

    Hue is kept exactly as measured. Only saturation and lightness move, and
    only as far as the bounds require, so a colour already in range comes back
    unchanged.
    """
    hue, saturation, value = to_hsv(rgb)
    saturation = clamp(saturation, bounds['min_sat'], bounds['max_sat'])
    value = clamp(value, bounds['min_val'], bounds['max_val'])
    return to_hex([c * 255 for c in colorsys.hsv_to_rgb(hue, saturation, value)])


def load_image(path):
    """Open a photo with its EXIF rotation already applied.

    Phone photos carry orientation in EXIF rather than in the pixel data. A
    resize does not consult it, so skipping this silently turns a portrait
    shot on its side in the grid while the original still looks upright.
    """
    from PIL import Image, ImageOps

    image = Image.open(path)
    image = ImageOps.exif_transpose(image)
    return image.convert('RGB')


def existing_size(path):
    """The pixel size of a derivative already on disk.

    Reads the header only; Pillow does not decode the image for this.
    """
    from PIL import Image

    with Image.open(path) as image:
        return image.size


def write_derivative(image, destination, target_width, quality):
    """Write one resized copy, and report the size it was written at."""
    from PIL import Image

    size = scaled_size(image.size, target_width)
    resized = image.resize(size, Image.LANCZOS) if size != image.size else image
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    resized.save(destination, 'JPEG', quality=quality, optimize=True,
                 progressive=True)
    return size


def make_lqip(image):
    """A 16 px-wide JPEG of the photo, as an inline data URI."""
    from PIL import Image

    size = scaled_size(image.size, LQIP_WIDTH)
    tiny = image.resize(size, Image.LANCZOS)
    buffer = io.BytesIO()
    tiny.save(buffer, 'JPEG', quality=LQIP_QUALITY, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return 'data:image/jpeg;base64,' + encoded


def score_cluster(share, saturation, value):
    """How well a quantised cluster represents the photo.

    Prominence times saturation, damped away from mid-tones so a colour is
    picked that will still read once the accent bounds are applied.
    """
    return share * (saturation ** SATURATION_BIAS) * (1 - abs(value - 0.55))


def dominant_colour(image):
    """The photo's most characteristic colour.

    See the notes on SKY_CROP above for why this is not a mean.
    """
    from PIL import Image

    sample = image.copy()
    sample.thumbnail(SAMPLE_BOX, Image.LANCZOS)
    width, height = sample.size
    sample = sample.crop((0, int(height * SKY_CROP), width, height))

    quantised = sample.quantize(colors=QUANT_COLOURS, method=Image.MEDIANCUT)
    palette = quantised.getpalette()[:QUANT_COLOURS * 3]
    # getcolors() yields (count, index) pairs -- in that order.
    counts = {index: count for count, index in quantised.getcolors()}
    total = float(sum(counts.values()))

    best, best_score = None, -1.0
    for index, count in counts.items():
        rgb = tuple(palette[index * 3:index * 3 + 3])
        _, saturation, value = to_hsv(rgb)
        if value < 0.08 or value > 0.97:
            continue
        current = score_cluster(count / total, saturation, value)
        if current > best_score:
            best, best_score = rgb, current

    # Every cluster crushed or blown: fall back to the plain mean, which is at
    # least a colour the photo contains a lot of.
    if best is None:
        return image.resize((1, 1), Image.LANCZOS).getpixel((0, 0))
    return best


def build(entries, force=False, log=print):
    """Write every derivative and return the render data for the template."""
    photos = {}
    by_park = {}

    for entry in entries:
        original = gallery_data.original_path(entry)
        name = os.path.basename(original)
        targets = {kind: derivative_path(original, kind) for kind in SIZES}

        # The measurements are cheap only because the file is already decoded
        # for the resize, so a fully up-to-date photo is still opened once.
        image = load_image(original)
        colour = dominant_colour(image)

        record = {'lqip': make_lqip(image), 'colour': to_hex(colour)}
        for kind, target_width in sorted(SIZES.items()):
            if force or is_stale(original, targets[kind]):
                size = write_derivative(image, targets[kind], target_width,
                                        QUALITY[kind])
                action = 'wrote'
            else:
                # Measured from the file rather than recomputed from the
                # target width. The two agree until a width in SIZES changes,
                # at which point every existing derivative is a size the
                # arithmetic no longer predicts and the staleness check --
                # which only looks at mtimes -- does not notice.
                size = existing_size(targets[kind])
                action = 'kept '
            if kind == 'thumbs':
                record['width'], record['height'] = size
            log('  %s %s/%s  %dx%d' % (action, kind, name, size[0], size[1]))
        image.close()

        photos[name] = record
        park = entry.get('park')
        if park:
            by_park.setdefault(park, []).append(colour)

    parks = {}
    for park, colours in sorted(by_park.items()):
        combined = combine_colours(colours)
        parks[park] = {
            'colour': to_hex(combined),
            'accent': accent(combined, ACCENT_LIGHT),
            'accent_dark': accent(combined, ACCENT_DARK),
        }

    return {'photos': photos, 'parks': parks}


def directory_bytes(path):
    if not os.path.isdir(path):
        return 0
    return sum(os.path.getsize(os.path.join(path, n)) for n in os.listdir(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--force', action='store_true',
                        help='rebuild every derivative, not just stale ones')
    args = parser.parse_args()

    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit('Pillow is needed for this script but is not installed.\n'
                 'Install it with:  python3 -m pip install -r '
                 'requirements-dev.txt\n'
                 '(build.py and CI do not need it -- only this script does.)')

    entries = gallery_data.load_gallery()
    render = build(entries, force=args.force)

    destination = os.path.join(DATA, 'gallery_render.json')
    with open(destination, 'w', encoding='utf-8') as handle:
        json.dump(render, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write('\n')

    originals = directory_bytes(GALLERY)
    thumbs = directory_bytes(os.path.join(GALLERY, 'thumbs'))
    large = directory_bytes(os.path.join(GALLERY, 'large'))
    print('\n%d photos across %d parks' % (len(render['photos']),
                                           len(render['parks'])))
    print('  originals  %7.1f MB  (kept as the source; never served)'
          % (originals / 1e6))
    print('  thumbs     %7.1f MB  (what the grid now costs)' % (thumbs / 1e6))
    print('  large      %7.1f MB  (one file per lightbox open)' % (large / 1e6))
    print('  wrote _data/gallery_render.json (%.1f KB)'
          % (os.path.getsize(destination) / 1024.0))


if __name__ == '__main__':
    main()
