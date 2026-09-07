#!/usr/bin/env python3
"""Turn docs/_logs/trails.md into docs/_data/trails.json for the Adventure page.

Two modes, the same contract as build_covers.py:

    python3 scripts/build_trails.py            # offline, no network at all
    python3 scripts/build_trails.py --fetch    # look up new trails in OSM

The offline mode is what build.py and CI run: it parses the log, merges in
whatever is already in the committed cache, and touches the network never, so
the build stays deterministic. --fetch is the occasional manual pass that adds
newly logged trails to docs/_data/trails_osm.json.

Unlike the park checklists this is an open-ended log, not a finite universe
with a visited flag — there is no list of every trail to tick off, only the
ones actually walked.

Why the lookup is scoped to an area
-----------------------------------
Searching OpenStreetMap for a trail by name alone does not work: the query is
unindexed, so it either times out or misses ("Breakneck Ridge" returns
nothing globally). Scoping to a named area is indexed and fast, which is why
the log's "where" field is required to resolve anything. Geocoding the place
first would work too, but that means a second service; one Overpass call per
trail keeps this to a single keyless dependency.

What comes back varies by region, and both shapes are worth having:

  - Blazed networks (the Northeast, most of Europe) carry osmc:symbol or
    colour — the actual paint on the tree.
  - National park trails are rarely blazed but usually carry sac_scale (a
    difficulty grade), surface, and sometimes an official distance.
"""

import argparse
import collections
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'docs', '_data')
LOG_PATH = os.path.join(ROOT, 'docs', '_logs', 'trails.md')
OUT_PATH = os.path.join(DATA, 'trails.json')
CACHE_PATH = os.path.join(DATA, 'trails_osm.json')

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'
USER_AGENT = 'kentayoshii.github.io trail build (github.com/KentaYoshii)'
# Overpass is donated infrastructure with a small number of concurrent slots.
# It answers 429 as soon as you run out of them, which a one-second gap is not
# enough to avoid, so a fetch run waits properly between trails and backs off
# when told to.
REQUEST_PAUSE = 3.0
REQUEST_TIMEOUT = 90
RETRY_STATUS = (429, 504)
RETRY_ATTEMPTS = 4
RETRY_BACKOFF = 15           # seconds, doubled per attempt
CHECKPOINT_EVERY = 10

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
MONTH_NUM = {m.lower(): i + 1 for i, m in enumerate(MONTHS)}

# A hiking route relation, or the named ways most park trails are tagged as.
# Capped with "out tags N" because a long trail is hundreds of way segments
# and only their tags are wanted, never their geometry.
QUERY = '''
[out:json][timeout:%(timeout)d];
area["name"=%(area)s]->.a;
(
  relation(area.a)["route"="hiking"]["name"=%(name)s];
  way(area.a)["highway"~"path|footway|track|steps"]["name"=%(name)s];
);
out tags 30;
'''

# Tags worth keeping, in the order the page shows them. Everything else in
# OSM's very long tail is dropped rather than carried into the data file.
KEEP_TAGS = ('osmc:symbol', 'colour', 'symbol', 'distance', 'sac_scale',
             'trail_visibility', 'surface', 'operator', 'network', 'website')

# sac_scale is a six-step Alpine grading. The raw values read as jargon on a
# personal site, so they are relabelled — but not collapsed, because the
# distinction between a walk and a scramble is the interesting part.
SAC_LABELS = {
    'hiking': 'easy',
    'mountain_hiking': 'moderate',
    'demanding_mountain_hiking': 'demanding',
    'alpine_hiking': 'alpine',
    'demanding_alpine_hiking': 'demanding alpine',
    'difficult_alpine_hiking': 'difficult alpine',
}

MILES_PER_KM = 0.621371


def keyify(s):
    return re.sub(r'[^a-z0-9]+', '', (s or '').lower())


# ---- the log ----------------------------------------------------------------

# Split on an em dash, an en dash, or a double hyphen. Deliberately not a
# lone " - ": trail names contain it ("Suffern - Bear Mountain Trail").
FIELD_SPLIT = re.compile(r'\s+(?:—|–|--)\s+')
DISTANCE_RE = re.compile(r'^([\d.]+)\s*(mi|mile|miles|km|k)\b', re.I)


def parse_distance(text):
    """'6.2 mi' -> (6.2, 'mi'); '10 km' -> (6.21, 'mi'). Miles because the
    rest of the log is US-centric; the original text is kept for display."""
    m = DISTANCE_RE.match((text or '').strip())
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith('k'):
        value *= MILES_PER_KM
    return round(value, 2)


def area_of(place):
    """The OSM area name to scope a lookup to: the part before the first
    comma, so 'Zion National Park, UT' searches inside Zion."""
    return (place or '').split(',')[0].strip()


def parse_log(path=None):
    """[{name, place, area, distance_mi, distance_text, year, month, date}]."""
    entries = []
    year = None
    month = None
    for line in open(path or LOG_PATH, encoding='utf-8'):
        line = line.rstrip()

        head = re.match(r'^##\s+(.+?)\s*$', line)
        if head:
            label = head.group(1).strip()
            year = label if re.fullmatch(r'\d{4}', label) else None
            month = None
            continue

        sub = re.match(r'^###\s+(.+?)\s*$', line)
        if sub:
            label = sub.group(1).strip()
            month = label if label.lower() in MONTH_NUM else None
            continue

        item = re.match(r'^-\s+(.+?)\s*$', line)
        if not item or not year:
            continue

        parts = [p.strip() for p in FIELD_SPLIT.split(item.group(1))]
        name = parts[0]
        if not name:
            continue

        place = parts[1] if len(parts) > 1 else ''
        distance_text = parts[2] if len(parts) > 2 else ''
        # Two fields where the second is a distance means the place was
        # omitted, not that the distance is a place.
        if place and not distance_text and parse_distance(place) is not None:
            distance_text, place = place, ''

        entries.append({
            'name': name,
            'place': place,
            'area': area_of(place),
            'distance_mi': parse_distance(distance_text),
            'distance_text': distance_text,
            'year': year,
            'month': month,
            # Sortable stamp; a hike with no month sorts to the start of its
            # year, matching how build_movies.py handles the same gap.
            'date': '%s-%02d' % (year, MONTH_NUM.get((month or '').lower(), 0)),
        })
    return entries


# ---- OSM --------------------------------------------------------------------

def cache_key(entry):
    """Name plus area: the same trail name in two parks is two trails."""
    return '%s|%s' % (keyify(entry['name']), keyify(entry['area']))


def load_cache():
    try:
        with open(CACHE_PATH, encoding='utf-8') as f:
            cache = json.load(f)
    except (OSError, ValueError):
        return {}
    return cache if isinstance(cache, dict) else {}


def save_cache(cache):
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')


def overpass(name, area, sleep=time.sleep):
    """One Overpass query, retrying while it says it is busy.

    429 (no free slot) and 504 (query timed out under load) are both transient
    and both routine on the public instance. Retrying with a widening gap is
    the documented way to be a good citizen; anything else is raised.
    """
    body = QUERY % {'timeout': REQUEST_TIMEOUT - 30,
                    'area': json.dumps(area),
                    'name': json.dumps(name)}
    delay = RETRY_BACKOFF

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        req = urllib.request.Request(OVERPASS_URL, data=body.encode(),
                                     headers={'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRY_STATUS or attempt == RETRY_ATTEMPTS:
                raise
            print('      overpass busy (%d), waiting %ds' % (exc.code, delay))
            sleep(delay)
            delay *= 2

    raise AssertionError('unreachable')   # the loop always returns or raises


# Tags that only mean anything on a route relation. "distance" is the trap:
# on a relation it is the length of the whole route, but on a single way it is
# the length of that one segment — merging the two put an official 2.98 mi
# against a logged 17.3 mi on the Hoh River Trail.
RELATION_ONLY_TAGS = ('distance',)


def lookup(name, area):
    """The tags OSM has for this trail, or {} if it does not resolve.

    A trail is many way segments, tagged inconsistently — one stretch records
    the surface, another the difficulty. Merging keeps the first value seen
    for each tag rather than trusting any single segment to be complete.
    Relations are read first, so a route-level tag wins over a segment's.
    """
    elements = (overpass(name, area) or {}).get('elements') or []
    merged = {}
    # Relations first: their tags describe the whole trail.
    for element in sorted(elements, key=lambda e: e.get('type') != 'relation'):
        is_relation = element.get('type') == 'relation'
        for key, value in (element.get('tags') or {}).items():
            if key not in KEEP_TAGS or key in merged:
                continue
            if key in RELATION_ONLY_TAGS and not is_relation:
                continue
            merged[key] = value
    if merged:
        merged['osm_elements'] = len(elements)
    return merged


def resolve_missing(entries, cache):
    """The --fetch pass. Only looks up keys not already cached; an empty dict
    is a cached "asked, nothing there" and is not retried."""
    pending = {}
    for entry in entries:
        if not entry['area']:
            continue        # nothing to scope a search to
        key = cache_key(entry)
        if key not in cache:
            pending[key] = entry

    if not pending:
        print('  nothing to look up; the cache already covers every trail')
        return

    print('  looking up %d trail(s) in OpenStreetMap' % len(pending))
    for i, (key, entry) in enumerate(sorted(pending.items()), start=1):
        tags = lookup(entry['name'], entry['area'])
        cache[key] = tags
        print('    %-34s %-24s %s' % (
            entry['name'][:34], entry['area'][:24],
            ', '.join('%s=%s' % kv for kv in sorted(tags.items())
                      if kv[0] != 'osm_elements')[:60] or '(nothing)'))
        if i % CHECKPOINT_EVERY == 0:
            save_cache(cache)
        time.sleep(REQUEST_PAUSE)
    save_cache(cache)


# ---- assembly ---------------------------------------------------------------

def blaze_of(tags):
    """A CSS colour for the trail blaze, or None.

    osmc:symbol is colon-separated: waycolour:background:foreground[:...].
    The waycolour is the paint on the tree and the only field worth showing;
    the rest describes the symbol's shape, which a swatch cannot render.
    """
    symbol = tags.get('osmc:symbol')
    if symbol:
        way_colour = symbol.split(':')[0].strip()
        if way_colour:
            return way_colour
    colour = (tags.get('colour') or '').strip()
    return colour or None


def decorate(entry, tags):
    """Merge one log entry with its OSM tags into a render-ready record."""
    official = None
    try:
        # OSM records route distance in kilometres.
        official = round(float(tags['distance']) * MILES_PER_KM, 2)
    except (KeyError, TypeError, ValueError):
        pass

    return {
        'name': entry['name'],
        'place': entry['place'],
        'year': entry['year'],
        'month': entry['month'],
        'date': entry['date'],
        'distance_mi': entry['distance_mi'],
        'distance_text': entry['distance_text'],
        'blaze': blaze_of(tags),
        'difficulty': SAC_LABELS.get(tags.get('sac_scale')),
        'surface': tags.get('surface'),
        'official_distance_mi': official,
        'resolved': bool(tags),
    }


def summarise(trails):
    by_year = collections.Counter(t['year'] for t in trails)
    logged = [t['distance_mi'] for t in trails if t['distance_mi']]
    return {
        'total': len(trails),
        'distance_mi': round(sum(logged), 1),
        'distance_counted': len(logged),
        'resolved': sum(1 for t in trails if t['resolved']),
        'by_year': [{'year': y, 'count': by_year[y]}
                    for y in sorted(by_year, reverse=True)],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--fetch', action='store_true',
        help='look up trails not in the cache yet (requires network)')
    # build.py calls main() with no arguments; argparse would otherwise read
    # sys.argv and choke on another script's flags.
    args = parser.parse_args([] if argv is None else argv)

    entries = parse_log()
    cache = load_cache()
    failed = False

    if args.fetch:
        try:
            resolve_missing(entries, cache)
        except (urllib.error.URLError, OSError) as exc:
            # Fall through rather than returning: whatever was resolved before
            # the failure is in the cache, and the data file should reflect it
            # instead of waiting for a separate offline run.
            failed = True
            print('  lookup stopped: %s' % exc, file=sys.stderr)
            print('  keeping what resolved; re-run --fetch to continue',
                  file=sys.stderr)

    trails = [decorate(e, cache.get(cache_key(e)) or {}) for e in entries]
    # Most recent first — unlike Books and Movies, which are browsed
    # alphabetically, a trail log reads as a diary.
    trails.sort(key=lambda t: (t['date'], t['name']), reverse=True)

    wanted = {cache_key(e) for e in entries}
    dropped = len(set(cache) - wanted)
    cache = {k: v for k, v in cache.items() if k in wanted}

    payload = {'trails': trails, 'summary': summarise(trails)}
    os.makedirs(DATA, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write('\n')
    save_cache(cache)

    summary = payload['summary']
    print('wrote %d trail(s) -> %s'
          % (summary['total'], os.path.relpath(OUT_PATH, ROOT)))
    if summary['total']:
        print('  %s miles across %d logged distance(s)'
              % (summary['distance_mi'], summary['distance_counted']))
        print('  %d of %d matched in OpenStreetMap'
              % (summary['resolved'], summary['total']))
    if dropped:
        print('  dropped %d stale cache entr%s'
              % (dropped, 'y' if dropped == 1 else 'ies'))
    unresolved = summary['total'] - summary['resolved']
    if unresolved:
        print('  %d unresolved — run with --fetch to look them up' % unresolved)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
