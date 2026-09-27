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
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'docs', '_data')
LOG_PATH = os.path.join(ROOT, 'docs', '_logs', 'trails.md')
OUT_PATH = os.path.join(DATA, 'trails.json')

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


# ---- assembly ---------------------------------------------------------------

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
    # Most recent first — unlike Books and Movies, which are browsed
    # alphabetically, a trail log reads as a diary. By date only: the sort is
    # stable (reverse=True included), so hikes within a month keep the order
    # they are written in the log, which keeps one park's hikes together.
    trails.sort(key=lambda t: t['date'], reverse=True)

    payload = {'trails': trails, 'summary': summarise(trails)}
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
    return 0


if __name__ == '__main__':
    main()
