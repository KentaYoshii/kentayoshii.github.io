#!/usr/bin/env python3
"""Turn docs/_logs/trails.md into docs/_data/trails.json for the Adventure page.

    python3 scripts/build_trails.py

Offline and deterministic: everything on the page is what the log says. The
distance and elevation gain are typed by hand rather than looked up, because
most hikes worth logging are loops or combinations ("Paintbrush–Cascade Canyon
Loop") that no map database holds under a single name.

Unlike the park checklists this is an open-ended log, not a finite universe
with a visited flag — there is no list of every trail to tick off, only the
ones actually walked.
"""

import collections
import difflib
import json
import os
import re
import sys

import gallery_data

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'docs', '_data')
LOG_PATH = os.path.join(ROOT, 'docs', '_logs', 'trails.md')
OUT_PATH = os.path.join(DATA, 'trails.json')
# Written by build_travel.py, which build.py runs first. Read only for the
# national park names, so a hike can be matched to its park.
TRAVEL_PATH = os.path.join(DATA, 'travel.json')
# Photos carry an optional `trail`, the name of the hike they were taken on.
GALLERY_PATH = gallery_data.GALLERY_YML
PARK_SUFFIX = ' National Park'

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
MONTH_NUM = {m.lower(): i + 1 for i, m in enumerate(MONTHS)}

MILES_PER_KM = 0.621371
FEET_PER_METRE = 3.28084


# ---- the log ----------------------------------------------------------------

# Split on an em dash, an en dash, or a double hyphen. Deliberately not a
# lone " - ": trail names contain it ("Suffern - Bear Mountain Trail").
FIELD_SPLIT = re.compile(r'\s+(?:—|–|--)\s+')
DISTANCE_RE = re.compile(r'^([\d.]+)\s*(mi|mile|miles|km|k)\b', re.I)
# "m" alone is metres here; miles are always written mi/mile/miles, which
# DISTANCE_RE claims first.
ELEVATION_RE = re.compile(r'^([\d,.]+)\s*(ft|feet|foot|m|metres|meters)\b', re.I)


def parse_distance(text):
    """'6.2 mi' -> 6.2; '10 km' -> 6.21. Miles because the rest of the log is
    US-centric; the original text is kept for display."""
    m = DISTANCE_RE.match((text or '').strip())
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith('k'):
        value *= MILES_PER_KM
    return round(value, 2)


def parse_elevation(text):
    """'4,350 ft' -> 4350; '450 m' -> 1476. Whole feet: a gain quoted to a
    fraction of a foot would be false precision."""
    m = ELEVATION_RE.match((text or '').strip())
    if not m:
        return None
    try:
        value = float(m.group(1).replace(',', ''))
    except ValueError:
        return None          # "1.2.3 ft"
    if m.group(2).lower().startswith('m'):
        value *= FEET_PER_METRE
    return int(round(value))


def parse_log(path=None):
    """[{name, place, distance_mi, distance_text, elevation_ft,
    elevation_text, year, month, date}]."""
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

        # After the name, each field is recognised by what it parses as rather
        # than by position, so a hike logged without a place still has its
        # distance read as a distance and not shown as a place called "4 mi".
        place = distance_text = elevation_text = ''
        for field in parts[1:]:
            if not distance_text and parse_distance(field) is not None:
                distance_text = field
            elif not elevation_text and parse_elevation(field) is not None:
                elevation_text = field
            elif not place:
                place = field

        entries.append({
            'name': name,
            'place': place,
            'distance_mi': parse_distance(distance_text),
            'distance_text': distance_text,
            'elevation_ft': parse_elevation(elevation_text),
            'elevation_text': elevation_text,
            'year': year,
            'month': month,
            # Sortable stamp; a hike with no month sorts to the start of its
            # year, matching how build_movies.py handles the same gap.
            'date': '%s-%02d' % (year, MONTH_NUM.get((month or '').lower(), 0)),
        })
    return entries


# ---- parks ------------------------------------------------------------------

def load_park_names(path=None):
    """The national park names from travel.json, or an empty set if it is
    missing or unreadable -- hikes then just go unmatched."""
    try:
        with open(path or TRAVEL_PATH, encoding='utf-8') as f:
            items = json.load(f)['checklists']['us_national_parks']['items']
        return {item['name'] for item in items}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def park_of(place, park_names):
    """The checklist name of the national park a place is in, or None.

    'Glacier National Park, MT' -> 'Glacier'. The name has to match
    travel.json exactly, because the parks page and its colours key on it.
    """
    area = (place or '').split(',')[0].strip()
    if area.endswith(PARK_SUFFIX):
        area = area[:-len(PARK_SUFFIX)]
    return area if area in park_names else None


def unmatched_parks(trails, park_names):
    """[(place, suggestion)] for hikes whose place names a national park that
    is not in the checklist -- almost always a typo, which would otherwise
    only show as a heading with no colour and a park total that is short.
    suggestion is the closest checklist name, or None."""
    found = []
    for trail in trails:
        area = (trail['place'] or '').split(',')[0].strip()
        if trail['park'] or not area.endswith(PARK_SUFFIX):
            continue
        close = difflib.get_close_matches(area[:-len(PARK_SUFFIX)],
                                          sorted(park_names), n=1)
        pair = (trail['place'], close[0] if close else None)
        if pair not in found:
            found.append(pair)
    return found


def label_of(place, park):
    """What a group of hikes is headed with: the park name, or for a hike
    outside a national park the place up to its first comma."""
    return park or (place or '').split(',')[0].strip()


# ---- photos -----------------------------------------------------------------

def load_photos(path=None):
    """The gallery entries, or [] if gallery.yml is missing -- hikes then
    just have no photos."""
    try:
        return gallery_data.load_gallery(path or GALLERY_PATH)
    except OSError:
        return []


def attach_photos(trails, photos):
    """Give each hike the file names of the photos taken on it, in gallery
    order, and return the photos whose `trail` matched no hike.

    A photo matches on park and trail name together, so two parks can each
    have a hike of the same name. The file name is all the page needs: it
    looks the rest up in gallery.yml and gallery_render.json, as the parks
    page does.
    """
    by_key = {}
    for trail in trails:
        trail['photos'] = []
        by_key.setdefault((trail['park'], trail['name']), trail)

    stray = []
    for photo in photos:
        name = photo.get('trail')
        if not name:
            continue
        trail = by_key.get((photo.get('park'), name))
        if trail is None:
            stray.append(photo)
        else:
            trail['photos'].append(photo['image'].split('/')[-1])
    return stray


# ---- assembly ---------------------------------------------------------------

def miles_text(miles):
    """95.4 -> '95.4', 5.0 -> '5'. Formatted here because Liquid cannot."""
    return '{:g}'.format(round(miles, 1))


def totals(trails):
    distance = sum(t['distance_mi'] or 0 for t in trails)
    elevation = sum(t['elevation_ft'] or 0 for t in trails)
    return {
        'count': len(trails),
        'distance_mi': round(distance, 1),
        'distance_text': miles_text(distance),
        'elevation_ft': elevation,
        'elevation_text': '{:,}'.format(elevation),
    }


def group(trails):
    """Consecutive hikes in the same month and place, as one group each.

    Consecutive rather than all hikes per park: the page is a diary, so a park
    visited in two different months appears twice. The first (most recent)
    group of each park is flagged, so the page can give it the anchor the
    parks page links to.
    """
    groups = []
    seen = set()
    for trail in trails:
        key = (trail['date'], trail['label'])
        if not groups or groups[-1]['key'] != key:
            groups.append({'key': key, 'trails': []})
        groups[-1]['trails'].append(trail)

    out = []
    for g in groups:
        first = g['trails'][0]
        park = first['park']
        entry = {
            'year': first['year'],
            'month': first['month'],
            'park': park,
            'label': first['label'],
            'first_of_park': bool(park) and park not in seen,
            'trails': g['trails'],
        }
        entry.update(totals(g['trails']))
        out.append(entry)
        if park:
            seen.add(park)
    return out


def by_park(trails):
    """{park: totals} across every visit, for the parks page."""
    parks = collections.OrderedDict()
    for trail in trails:
        if trail['park']:
            parks.setdefault(trail['park'], []).append(trail)
    return {park: totals(hikes) for park, hikes in parks.items()}


def add_gain_share(trails):
    """Give each hike its gain as a whole percentage of the biggest in the
    log, for the bar beside the figure. None where no gain is logged, so the
    page draws no bar rather than an empty one that reads as zero."""
    biggest = max((t['elevation_ft'] or 0 for t in trails), default=0)
    for trail in trails:
        gain = trail['elevation_ft']
        trail['gain_pct'] = (max(1, int(round(100.0 * gain / biggest)))
                             if gain and biggest else None)


def records(trails, parks):
    """The longest hike, the biggest climb, and the park with the most
    miles, or {} for an empty log. Ties go to the more recent, since trails
    arrive newest first and max() keeps the first it sees."""
    out = {}
    measured = [t for t in trails if t['distance_mi']]
    if measured:
        t = max(measured, key=lambda t: t['distance_mi'])
        out['longest'] = {'name': t['name'], 'park': t['park'],
                          'text': t['distance_text']}
    climbed = [t for t in trails if t['elevation_ft']]
    if climbed:
        t = max(climbed, key=lambda t: t['elevation_ft'])
        out['climb'] = {'name': t['name'], 'park': t['park'],
                        'text': t['elevation_text']}
    if parks:
        name = max(parks, key=lambda p: parks[p]['distance_mi'])
        if parks[name]['distance_mi']:
            out['park'] = {'name': name, 'park': name,
                           'text': parks[name]['distance_text'] + ' mi'}
    return out


def summarise(trails):
    by_year = collections.Counter(t['year'] for t in trails)
    logged = [t['distance_mi'] for t in trails if t['distance_mi']]
    climbed = [t['elevation_ft'] for t in trails if t['elevation_ft']]
    return {
        'total': len(trails),
        'distance_mi': round(sum(logged), 1),
        'distance_counted': len(logged),
        'elevation_ft': sum(climbed),
        # Pre-formatted because Liquid has no thousands separator.
        'elevation_text': '{:,}'.format(sum(climbed)),
        'elevation_counted': len(climbed),
        'by_year': [{'year': y, 'count': by_year[y]}
                    for y in sorted(by_year, reverse=True)],
    }


def main():
    trails = parse_log()
    park_names = load_park_names()
    for trail in trails:
        trail['park'] = park_of(trail['place'], park_names)
        trail['label'] = label_of(trail['place'], trail['park'])
    # A warning, not a failure: the hike still renders, just unmatched.
    if park_names:
        for place, suggestion in unmatched_parks(trails, park_names):
            hint = ' (did you mean %s?)' % suggestion if suggestion else ''
            print('  warning: %r is not a park in the checklist%s'
                  % (place, hint), file=sys.stderr)
    # Most recent first — unlike Books and Movies, which are browsed
    # alphabetically, a trail log reads as a diary. By date only: the sort is
    # stable (reverse=True included), so hikes within a month keep the order
    # they are written in the log, which keeps one park's hikes together.
    trails.sort(key=lambda t: t['date'], reverse=True)

    # No flat list of hikes: each one is already inside its group, and the
    # pages read the groups, the per-park totals, or the summary.
    add_gain_share(trails)
    for photo in attach_photos(trails, load_photos()):
        print('  warning: %s names trail %r, which is not a logged hike in %s'
              % (photo['image'], photo['trail'], photo.get('park') or 'no park'),
              file=sys.stderr)
    parks = by_park(trails)
    payload = {'groups': group(trails), 'parks': parks,
               'records': records(trails, parks), 'summary': summarise(trails)}
    os.makedirs(DATA, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write('\n')

    summary = payload['summary']
    print('wrote %d trail(s) -> %s'
          % (summary['total'], os.path.relpath(OUT_PATH, ROOT)))
    if summary['total']:
        print('  %s miles across %d logged distance(s)'
              % (summary['distance_mi'], summary['distance_counted']))
        print('  %s ft of gain across %d logged elevation(s)'
              % (summary['elevation_ft'], summary['elevation_counted']))
        print('  %d in national parks, %d park(s)'
              % (sum(1 for t in trails if t['park']), len(payload['parks'])))
    return 0


if __name__ == '__main__':
    main()
