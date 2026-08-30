#!/usr/bin/env python3
"""Cross-reference docs/_logs/travel.md against the fixed National Parks
reference list into docs/_data/travel.json, which the Travel page renders
as a checklist.

Run after editing the log:

    python3 scripts/build_travel.py

Unlike books and movies, "National Parks" has a known, finite universe
(scripts/national_parks.py) — the output is not just what you logged, it's
all 63 parks with a visited flag, so the page can show what's left too.
"""

import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOG_PATH = os.path.join(ROOT, 'docs', '_logs', 'travel.md')
OUT_PATH = os.path.join(ROOT, 'docs', '_data', 'travel.json')

sys.path.insert(0, HERE)
import national_parks  # noqa: E402

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']


def fold(s):
    """Strip diacritics (Haleakalā -> Haleakala) so a plain-ASCII log entry
    matches the reference list's accented official names."""
    return ''.join(c for c in unicodedata.normalize('NFKD', s)
                   if not unicodedata.combining(c))


def keyify(s):
    return re.sub(r'[^a-z0-9]+', '', fold(s).lower())


def parse_log():
    """Category -> [(year, month_or_None, raw_name), ...]."""
    categories = {}
    category = None
    year = None
    month = None
    for line in open(LOG_PATH, encoding='utf-8'):
        line = line.rstrip()
        cat = re.match(r'^##\s+(.+?)\s*$', line)
        if cat:
            category = cat.group(1)
            categories.setdefault(category, [])
            year = None
            month = None
            continue
        yr = re.match(r'^###\s+(.+?)\s*$', line)
        if yr and category:
            label = yr.group(1)
            if re.fullmatch(r'\d{4}', label):
                year = label
                month = None
            elif label in MONTHS:
                month = label
            continue
        item = re.match(r'^-\s+(.+?)\s*$', line)
        if item and category and year:
            categories[category].append((year, month, item.group(1).strip()))
    return categories


def match_park(raw_name, remaining):
    """The canonical park name raw_name refers to, from the parks in
    `remaining` (a dict keyed by keyify'd name), or None with a printed
    warning. Tries, in order: an explicit alias, an exact match, then an
    unambiguous prefix match in either direction ('Guadalupe' -> 'Guadalupe
    Mountains', 'Rocky Mountains' -> 'Rocky Mountain')."""
    aliased = national_parks.ALIASES.get(raw_name, raw_name)
    key = keyify(aliased)

    if key in remaining:
        return remaining[key]

    prefix_hits = [name for k, name in remaining.items()
                   if k.startswith(key) or key.startswith(k)]
    if len(prefix_hits) == 1:
        return prefix_hits[0]
    if len(prefix_hits) > 1:
        print('  ! "%s" matches multiple parks (%s) — add it to ALIASES in '
              'national_parks.py to disambiguate' % (raw_name, ', '.join(prefix_hits)),
              file=sys.stderr)
        return None

    print('  ! "%s" does not match any national park — typo, or a park not yet '
          'in national_parks.py?' % raw_name, file=sys.stderr)
    return None


def main():
    categories = parse_log()
    entries = categories.get('National Parks', [])

    # keyify -> canonical name, so multiple entries reduce to the same key on
    # a repeat visit without complaint (only the earliest visit is kept).
    by_key = {keyify(name): name for name, _ in national_parks.NATIONAL_PARKS}
    state_of = dict(national_parks.NATIONAL_PARKS)

    visited = {}   # canonical name -> (year, month)
    unmatched = 0
    for year, month, raw_name in entries:
        park = match_park(raw_name, by_key)
        if park is None:
            unmatched += 1
            continue
        if park not in visited or year < visited[park][0]:
            visited[park] = (year, month)

    parks = []
    for name, state in national_parks.NATIONAL_PARKS:
        v = visited.get(name)
        parks.append({
            'name': name,
            'state': state,
            'visited': v is not None,
            'year': v[0] if v else None,
            'month': v[1] if v else None,
        })
    parks.sort(key=lambda p: p['name'])

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            'national_parks': {
                'visited': len(visited),
                'total': len(national_parks.NATIONAL_PARKS),
                'parks': parks,
            }
        }, f, ensure_ascii=False, indent=1)
        f.write('\n')

    print('wrote %d/%d national parks visited -> %s'
          % (len(visited), len(national_parks.NATIONAL_PARKS),
             os.path.relpath(OUT_PATH, ROOT)))
    if unmatched:
        print('  %d log entr%s did not match a park (see warnings above)'
              % (unmatched, 'y' if unmatched == 1 else 'ies'))


if __name__ == '__main__':
    main()
