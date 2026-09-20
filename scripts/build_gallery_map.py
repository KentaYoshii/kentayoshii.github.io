#!/usr/bin/env python3
"""Project a US map and the photographed parks onto it, for the gallery hero.

    python3 scripts/build_gallery_map.py            # offline, no network
    python3 scripts/build_gallery_map.py --fetch    # re-download the geometry

Offline mode reads the committed cache in docs/_data/gallery_map.json and
touches the network never, so build.py and CI stay deterministic -- the same
split build_covers.py and build_trails.py use. --fetch is the rare manual pass
that rebuilds it; state borders do not move, so in practice this is run once
and again only to change the simplification or the projection.

The geometry is us-atlas, which packages the US Census Bureau's cartographic
boundary files (public domain) as TopoJSON under an ISC licence. It arrives
unprojected, in plain longitude and latitude, and that is the reason it was
chosen over anything pre-rendered: the park markers have to land inside their
own states, and the only way to guarantee that is to run the outlines and the
markers through one projection implemented once. A pre-projected outline would
mean reimplementing whatever projection it used and hoping the two agreed.

That projection is Albers USA: an equal-area conic for the lower 48, with
Alaska and Hawaii moved in beside it on their own conics. Hawaii matters here
-- two of the fourteen parks are on Maui and Hawaiʻi island, and without the
inset they would be projected somewhere out in the Pacific, far off canvas.

Standard library only. Pillow is needed elsewhere in the gallery pipeline
(build_gallery_thumbs.py) but nothing here needs an image decoded.
"""

import argparse
import json
import math
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'docs', '_data')
MAP_JSON = os.path.join(DATA, 'gallery_map.json')

SOURCE_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json'
SOURCE_NAME = ('us-atlas@3 states-10m (US Census Bureau cartographic '
               'boundaries, public domain; ISC-licensed packaging)')

# The canvas d3's Albers USA defaults are tuned for. Keeping the stock scale
# and translate means the constants below are the published ones rather than
# numbers fitted by trial and error.
VIEW_WIDTH, VIEW_HEIGHT = 960, 500
SCALE = 1070.0
TRANSLATE = (480.0, 250.0)

# Simplification tolerance, in units of the projected canvas -- so ~0.7 of a
# pixel at the size the map is drawn. Above this the coastline visibly
# straightens; below it the committed file grows for detail nobody can see.
TOLERANCE = 0.7

# FIPS codes outside the fifty states and DC: Puerto Rico, Guam, American
# Samoa and the like. Albers USA has nowhere to put them, so they are dropped
# rather than projected into the Atlantic.
TERRITORY_FIPS = {'60', '66', '69', '72', '78'}
ALASKA_FIPS = '02'
HAWAII_FIPS = '15'

# Where each photographed park is, and the state it must land in. The second
# half of that is the point: a transposed sign or a digit typo produces a dot
# that still looks plausible on a map of this size, so every one of these is
# checked against the projected state polygon by the test suite rather than by
# eye. Names are travel.json's, so they join to the rest of the gallery.
PARKS = {
    'Big Bend': (29.2498, -103.2502, '48'),
    'Carlsbad Caverns': (32.1479, -104.5567, '35'),
    'Grand Canyon': (36.1069, -112.1129, '04'),
    'Grand Teton': (43.7904, -110.6818, '56'),
    'Guadalupe Mountains': (31.9231, -104.8677, '48'),
    'Haleakalā': (20.7204, -156.1552, '15'),
    'Hawaiʻi Volcanoes': (19.4194, -155.2885, '15'),
    'Mount Rainier': (46.8800, -121.7269, '53'),
    'Olympic': (47.8021, -123.6044, '53'),
    'Rocky Mountain': (40.3428, -105.6836, '08'),
    'White Sands': (32.7872, -106.3257, '35'),
    'Yellowstone': (44.4280, -110.5885, '56'),
    'Yosemite': (37.8651, -119.5383, '06'),
    'Zion': (37.2982, -113.0263, '49'),
}


class ConicEqualArea(object):
    """One Albers conic, matching d3-geo's conicEqualArea.

    Three details are easy to get subtly wrong and are spelled out here:

      - `rotate` is a shift in longitude applied before projecting, which is
        what puts the central meridian over the middle of the area of
        interest. Only longitude is rotated for these three projections, so
        the general three-axis spherical rotation is not needed.
      - `center` is NOT rotated. d3 feeds it straight into the raw projection
        when working out the translation offset, so it is expressed relative
        to the rotated meridian, not in geographic coordinates. Rotating it
        as well throws the whole map sideways by the rotation angle.
      - y grows downward on a canvas and northward on a globe, so the final
        step subtracts rather than adds.
    """

    def __init__(self, parallels, rotate_lon, center, scale, translate):
        phi0, phi1 = (math.radians(p) for p in parallels)
        sin_phi0 = math.sin(phi0)
        self.n = (sin_phi0 + math.sin(phi1)) / 2.0
        if abs(self.n) < 1e-10:
            raise ValueError('parallels %r degenerate to a cylinder' % (parallels,))
        self.c = 1 + sin_phi0 * (2 * self.n - sin_phi0)
        self.r0 = math.sqrt(self.c) / self.n

        self.rotate_lon = rotate_lon
        self.scale = float(scale)

        centre_x, centre_y = self._raw(math.radians(center[0]),
                                       math.radians(center[1]))
        self.dx = translate[0] - self.scale * centre_x
        self.dy = translate[1] + self.scale * centre_y

    def _raw(self, lam, phi):
        inner = self.c - 2 * self.n * math.sin(phi)
        # Goes negative only for points on the far side of the globe from the
        # cone, which nothing in a US dataset reaches.
        if inner < 0:
            raise ValueError('point outside the projection: %r' % (phi,))
        r = math.sqrt(inner) / self.n
        theta = lam * self.n
        return r * math.sin(theta), self.r0 - r * math.cos(theta)

    def __call__(self, lon, lat):
        lam = lon + self.rotate_lon
        # Normalise into [-180, 180) so a rotation does not push a longitude
        # past the antimeridian and wrap the point to the wrong side.
        lam = (lam + 180.0) % 360.0 - 180.0
        x, y = self._raw(math.radians(lam), math.radians(lat))
        return self.dx + self.scale * x, self.dy - self.scale * y


def albers_usa(scale=SCALE, translate=TRANSLATE):
    """The three sub-projections, with d3's offsets for the two insets."""
    x, y = translate
    return {
        'lower48': ConicEqualArea([29.5, 45.5], 96.0, (-0.6, 38.7),
                                  scale, (x, y)),
        'alaska': ConicEqualArea([55.0, 65.0], 154.0, (-2.0, 58.5),
                                 scale * 0.35,
                                 (x - 0.307 * scale, y + 0.201 * scale)),
        'hawaii': ConicEqualArea([8.0, 18.0], 157.0, (-3.0, 19.9),
                                 scale,
                                 (x - 0.205 * scale, y + 0.212 * scale)),
    }


def projection_for(fips, projections):
    if fips == ALASKA_FIPS:
        return projections['alaska']
    if fips == HAWAII_FIPS:
        return projections['hawaii']
    return projections['lower48']


def decode_arcs(topology):
    """Undo TopoJSON's delta encoding and quantisation into lon/lat arcs."""
    transform = topology.get('transform')
    arcs = []
    for encoded in topology['arcs']:
        x = y = 0
        points = []
        for dx, dy in encoded:
            x += dx
            y += dy
            if transform:
                sx, sy = transform['scale']
                tx, ty = transform['translate']
                points.append((x * sx + tx, y * sy + ty))
            else:
                points.append((float(x), float(y)))
        arcs.append(points)
    return arcs


def stitch(ring_indices, arcs):
    """Join a ring's arcs end to end.

    A negative index means that arc traversed backwards, encoded as the ones'
    complement so that -1 can refer to arc 0. Each arc repeats the previous
    arc's last point, so all but the first contribute from their second point.
    """
    ring = []
    for index in ring_indices:
        if index < 0:
            points = arcs[~index][::-1]
        else:
            points = arcs[index]
        ring.extend(points if not ring else points[1:])
    return ring


def rings_of(geometry, arcs):
    kind = geometry.get('type')
    if kind == 'Polygon':
        return [stitch(ring, arcs) for ring in geometry['arcs']]
    if kind == 'MultiPolygon':
        return [stitch(ring, arcs)
                for polygon in geometry['arcs'] for ring in polygon]
    if kind is None:
        return []
    raise ValueError('unexpected geometry type: %r' % (kind,))


def perpendicular_distance(point, start, end):
    (px, py), (x1, y1), (x2, y2) = point, start, end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    return abs(dy * px - dx * py + x2 * y1 - y2 * x1) / math.hypot(dx, dy)


def simplify(points, tolerance):
    """Douglas-Peucker, with an explicit stack rather than recursion.

    Not because recursion overflows here -- the deepest split this data needs
    is about 20 levels against a limit of 1000, since a coastline divides
    fairly evenly. It is written this way so the depth stops depending on the
    shape of third-party geometry that is re-fetched from time to time and
    could change.
    """
    if len(points) < 3 or tolerance <= 0:
        return list(points)

    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        worst, worst_index = -1.0, first
        for i in range(first + 1, last):
            d = perpendicular_distance(points[i], points[first], points[last])
            if d > worst:
                worst, worst_index = d, i
        if worst > tolerance:
            keep[worst_index] = True
            stack.append((first, worst_index))
            stack.append((worst_index, last))

    return [p for p, k in zip(points, keep) if k]


def to_path(rings, places=1):
    """SVG path data for a set of projected rings."""
    parts = []
    for ring in rings:
        # Two points cannot enclose an area; a ring reduced that far by
        # simplification is a sliver island and is dropped rather than drawn
        # as a hairline.
        if len(ring) < 3:
            continue
        chunks = []
        for i, (x, y) in enumerate(ring):
            chunks.append('%s%.*f,%.*f' % ('M' if i == 0 else 'L',
                                           places, x, places, y))
        parts.append(''.join(chunks) + 'Z')
    return ''.join(parts)


def build(topology, scale=SCALE, translate=TRANSLATE, tolerance=TOLERANCE):
    """Project and simplify every state, and place every park."""
    projections = albers_usa(scale, translate)
    arcs = decode_arcs(topology)

    states = []
    for geometry in topology['objects']['states']['geometries']:
        fips = geometry['id']
        if fips in TERRITORY_FIPS:
            continue
        project = projection_for(fips, projections)
        rings = []
        for ring in rings_of(geometry, arcs):
            projected = [project(lon, lat) for lon, lat in ring]
            rings.append(simplify(projected, tolerance))
        path = to_path(rings)
        if not path:
            continue
        states.append({
            'id': fips,
            'name': geometry['properties']['name'],
            'path': path,
        })
    states.sort(key=lambda s: s['name'])

    parks = []
    for name in sorted(PARKS):
        lat, lon, fips = PARKS[name]
        x, y = projection_for(fips, projections)(lon, lat)
        parks.append({'name': name, 'state': fips,
                      'x': round(x, 1), 'y': round(y, 1)})

    return {
        'source': SOURCE_NAME,
        'view': {'width': VIEW_WIDTH, 'height': VIEW_HEIGHT},
        'states': states,
        'parks': parks,
    }


def fetch_topology(url=SOURCE_URL):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--fetch', action='store_true',
                        help='re-download the geometry and rebuild the cache')
    args = parser.parse_args()

    if not args.fetch:
        if not os.path.exists(MAP_JSON):
            sys.exit('No committed map at %s.\nRun this once with --fetch to '
                     'build it.' % os.path.relpath(MAP_JSON, ROOT))
        with open(MAP_JSON, encoding='utf-8') as handle:
            existing = json.load(handle)
        print('%s: %d states, %d parks (offline; --fetch to rebuild)'
              % (os.path.relpath(MAP_JSON, ROOT), len(existing['states']),
                 len(existing['parks'])))
        return

    print('fetching %s' % SOURCE_URL)
    try:
        topology = fetch_topology()
    except Exception as error:
        sys.exit('Could not fetch the geometry: %s\n'
                 'The committed map is unchanged.' % error)

    result = build(topology)
    with open(MAP_JSON, 'w', encoding='utf-8') as handle:
        json.dump(result, handle, indent=1, sort_keys=True, ensure_ascii=False)
        handle.write('\n')

    points = sum(state['path'].count(',') for state in result['states'])
    print('wrote %s' % os.path.relpath(MAP_JSON, ROOT))
    print('  %d states, %d parks, %d points after simplification'
          % (len(result['states']), len(result['parks']), points))
    print('  %.1f KB' % (os.path.getsize(MAP_JSON) / 1024.0))


if __name__ == '__main__':
    main()
