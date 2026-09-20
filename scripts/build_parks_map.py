#!/usr/bin/env python3
"""Project a US map and every national park onto it, for /adventure/parks/.

    python3 scripts/build_parks_map.py            # offline, no network
    python3 scripts/build_parks_map.py --fetch    # re-download the geometry

Offline mode reads the committed cache in docs/_data/parks_map.json and
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
Alaska and Hawaii moved in beside it on their own conics. Both insets earn
their place: eight of the sixty-three parks are in Alaska and two are in
Hawaiʻi, and without them a sixth of the checklist would land out in the
ocean. Two parks -- American Samoa and Virgin Islands -- fall outside even
that, and are recorded in UNPLOTTABLE rather than forced somewhere wrong.

Standard library only. Pillow is needed elsewhere in the photo pipeline
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
MAP_JSON = os.path.join(DATA, 'parks_map.json')

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

# Every national park, by latitude and longitude. Keys are national_parks.py's
# names, which are also travel.json's, so a marker joins to its checklist entry
# and to any photographs of it.
#
# A typo here produces a dot that still looks perfectly plausible on a map this
# size, which is why none of these is trusted on sight: the test suite projects
# each one and checks it lands in the state national_parks.py says it is in. A
# transposed digit or a flipped sign moves a park hundreds of pixels, so the
# check separates mistakes from the handful of parks that are genuinely a
# fraction of a pixel offshore (see PROJECTION_TOLERANCE).
PARKS = {
    'Acadia': (44.3500, -68.2100),
    'American Samoa': (-14.2500, -170.6800),
    'Arches': (38.7300, -109.5900),
    'Badlands': (43.8550, -102.3400),
    'Big Bend': (29.2498, -103.2502),
    'Biscayne': (25.4900, -80.2100),
    'Black Canyon of the Gunnison': (38.5754, -107.7416),
    'Bryce Canyon': (37.5930, -112.1870),
    'Canyonlands': (38.2000, -109.9300),
    'Capitol Reef': (38.3670, -111.2620),
    'Carlsbad Caverns': (32.1479, -104.5567),
    'Channel Islands': (34.0069, -119.7785),
    'Congaree': (33.7948, -80.7821),
    'Crater Lake': (42.9446, -122.1090),
    'Cuyahoga Valley': (41.2808, -81.5678),
    'Death Valley': (36.5054, -117.0794),
    'Denali': (63.1148, -151.1926),
    'Dry Tortugas': (24.6285, -82.8732),
    'Everglades': (25.2866, -80.8987),
    'Gates of the Arctic': (67.9558, -153.8894),
    'Gateway Arch': (38.6247, -90.1848),
    'Glacier': (48.7596, -113.7870),
    'Glacier Bay': (58.6658, -136.9002),
    'Grand Canyon': (36.1069, -112.1129),
    'Grand Teton': (43.7904, -110.6818),
    'Great Basin': (38.9833, -114.3000),
    'Great Sand Dunes': (37.7916, -105.5943),
    'Great Smoky Mountains': (35.6118, -83.4895),
    'Guadalupe Mountains': (31.9231, -104.8677),
    'Haleakalā': (20.7204, -156.1552),
    'Hawaiʻi Volcanoes': (19.4194, -155.2885),
    'Hot Springs': (34.5217, -93.0424),
    'Indiana Dunes': (41.6533, -87.0524),
    'Isle Royale': (48.0063, -88.5547),
    'Joshua Tree': (33.8734, -115.9010),
    'Katmai': (58.5978, -154.9358),
    'Kenai Fjords': (59.9227, -149.6510),
    'Kings Canyon': (36.8879, -118.5551),
    'Kobuk Valley': (67.3556, -159.2836),
    'Lake Clark': (60.9672, -153.4178),
    'Lassen Volcanic': (40.4977, -121.4207),
    'Mammoth Cave': (37.1862, -86.1000),
    'Mesa Verde': (37.2309, -108.4618),
    'Mount Rainier': (46.8800, -121.7269),
    'New River Gorge': (37.9393, -81.0687),
    'North Cascades': (48.7718, -121.2985),
    'Olympic': (47.8021, -123.6044),
    'Petrified Forest': (34.9100, -109.8068),
    'Pinnacles': (36.4906, -121.1825),
    'Redwood': (41.2132, -124.0046),
    'Rocky Mountain': (40.3428, -105.6836),
    'Saguaro': (32.2967, -111.1666),
    'Sequoia': (36.4864, -118.5658),
    'Shenandoah': (38.2928, -78.6796),
    'Theodore Roosevelt': (46.9790, -103.5387),
    'Virgin Islands': (18.3428, -64.7486),
    'Voyageurs': (48.4839, -92.8386),
    'White Sands': (32.7872, -106.3257),
    'Wind Cave': (43.5724, -103.4818),
    'Wrangell–St. Elias': (61.7104, -142.9857),
    'Yellowstone': (44.4280, -110.5885),
    'Yosemite': (37.8651, -119.5383),
    'Zion': (37.2982, -113.0263),
}

# How far, in canvas pixels, a marker may sit outside the state it belongs to
# before the test suite calls it a mistake. Four parks need this and all four
# are real places the simplified outline does not reach:
#
#   Dry Tortugas   0.1px  islands seventy miles west of Key West
#   Biscayne       0.5px  almost entirely water off the Florida coast
#   Gateway Arch   0.6px  on the Mississippi bank; at this simplification the
#                         state line falls the wrong side of it
#   Isle Royale    1.1px  an island in Lake Superior
#
# A mistyped coordinate misses by hundreds of pixels, so 3 separates the two
# without being loose enough to let an error through.
PROJECTION_TOLERANCE = 3.0

# Albers USA covers the fifty states and nothing else. These two parks are
# real and are on the checklist; there is simply nowhere on this projection to
# draw them, so they are recorded here and the page says so rather than
# quietly showing 61 dots next to the number 63.
UNPLOTTABLE = ('American Samoa', 'Virgin Islands')


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
    """Which sub-projection a state's geometry belongs to."""
    if fips == ALASKA_FIPS:
        return projections['alaska']
    if fips == HAWAII_FIPS:
        return projections['hawaii']
    return projections['lower48']


def route(lat, lon):
    """Which sub-projection a point belongs to, or None if it has no home.

    Decided from the coordinate rather than from a state code entered by hand
    alongside it. One fewer field to get wrong, and it means a park that is
    nowhere near the United States reports that instead of being projected
    into the middle of Kansas.
    """
    if 51 <= lat <= 72 and (lon <= -129 or lon >= 172):
        return 'alaska'
    if 18 <= lat <= 23 and -161 <= lon <= -154:
        return 'hawaii'
    if 24 <= lat <= 50 and -125 <= lon <= -66:
        return 'lower48'
    return None


def place(name, projections, parks=None):
    """Project one park, or None where the projection has no room for it."""
    lat, lon = (parks or PARKS)[name]
    which = route(lat, lon)
    if which is None:
        return None
    x, y = projections[which](lon, lat)
    return round(x, 1), round(y, 1)


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

    # Sorted by name so the committed file has a stable order and a rebuild
    # produces no spurious diff. The page decides which markers to light up;
    # this only says where each one goes.
    parks = []
    for name in sorted(PARKS):
        point = place(name, projections)
        if point is None:
            continue
        parks.append({'name': name, 'x': point[0], 'y': point[1]})

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
