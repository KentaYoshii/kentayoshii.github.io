#!/usr/bin/env python3
"""Cross-reference docs/_logs/travel.md against fixed reference lists into
docs/_data/travel.json, which the Travel page renders as one checklist per
category.

Run after editing the log:

    python3 scripts/build_travel.py

Unlike books and movies, a category here has a known, finite universe — the
output is not just what you logged, it's every item with a visited flag, so
the page can show what's left too.

Adding a new category (e.g. Countries) needs three things, no changes to the
matching or output logic below:
  1. A reference list module, same shape as national_parks.py: a list of
     (name, subtitle) tuples plus an optional ALIASES dict.
  2. An entry in CHECKLISTS below.
  3. A "## <label>" section in docs/_logs/travel.md using that exact label.
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

# Log heading -> (json key, module). The heading text must match the log's
# "## " line exactly; the json key is what the Travel page's Liquid loop
# keys off. Order here is display order on the page.
CHECKLISTS = [
    ('US National Parks', 'us_national_parks', national_parks),
]


def fold(s):
    """Strip diacritics (Haleakalā -> Haleakala) so a plain-ASCII log entry
    matches a reference list's accented official names."""
    return ''.join(c for c in unicodedata.normalize('NFKD', s)
                   if not unicodedata.combining(c))


def keyify(s):
    return re.sub(r'[^a-z0-9]+', '', fold(s).lower())


def parse_log():
    """Category (the exact "## " heading text) -> [(year, month_or_None,
    raw_name), ...]."""
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


def match_item(raw_name, remaining, aliases, noun):
    """The canonical name raw_name refers to, from the items in `remaining`
    (a dict keyed by keyify'd name), or None with a printed warning. Tries,
    in order: an explicit alias, an exact match, then an unambiguous prefix
    match in either direction ('Guadalupe' -> 'Guadalupe Mountains',
    'Rocky Mountains' -> 'Rocky Mountain')."""
    aliased = aliases.get(raw_name, raw_name)
    key = keyify(aliased)

    if key in remaining:
        return remaining[key]

    prefix_hits = [name for k, name in remaining.items()
                   if k.startswith(key) or key.startswith(k)]
    if len(prefix_hits) == 1:
        return prefix_hits[0]
    if len(prefix_hits) > 1:
        print('  ! "%s" matches multiple %s (%s) — add an alias to disambiguate'
              % (raw_name, noun, ', '.join(prefix_hits)), file=sys.stderr)
        return None

    print('  ! "%s" does not match any %s — typo, or one missing from the '
          'reference list?' % (raw_name, noun[:-1] if noun.endswith('s') else noun),
          file=sys.stderr)
    return None


def build_checklist(label, entries, reference):
    """(json-ready dict, unmatched count) for one category. `reference` is a
    module exposing ITEMS (a list of (name, subtitle) tuples) and optionally
    ALIASES — the contract every checklist module in CHECKLISTS follows."""
    items = reference.ITEMS
    aliases = getattr(reference, 'ALIASES', {})
    noun = label.lower()

    by_key = {keyify(name): name for name, _ in items}

    visited = {}   # canonical name -> (year, month)
    unmatched = 0
    for year, month, raw_name in entries:
        name = match_item(raw_name, by_key, aliases, noun)
        if name is None:
            unmatched += 1
            continue
        if name not in visited or year < visited[name][0]:
            visited[name] = (year, month)

    out_items = []
    for name, subtitle in items:
        v = visited.get(name)
        out_items.append({
            'name': name,
            'subtitle': subtitle,
            'visited': v is not None,
            'year': v[0] if v else None,
            'month': v[1] if v else None,
        })
    out_items.sort(key=lambda i: i['name'])

    return {
        'label': label,
        'visited': len(visited),
        'total': len(items),
        'items': out_items,
    }, unmatched


def main():
    categories = parse_log()

    checklists = {}
    total_unmatched = 0
    for label, json_key, reference in CHECKLISTS:
        result, unmatched = build_checklist(label, categories.get(label, []), reference)
        checklists[json_key] = result
        total_unmatched += unmatched
        print('  %-20s %d/%d visited' % (label, result['visited'], result['total']))

    registered = {label for label, _, _ in CHECKLISTS}
    for label in categories:
        if label not in registered:
            print('  ! "## %s" in the log has no registered checklist — see the '
                  'module docstring to add one' % label, file=sys.stderr)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({'checklists': checklists}, f, ensure_ascii=False, indent=1)
        f.write('\n')

    print('wrote %s' % os.path.relpath(OUT_PATH, ROOT))
    if total_unmatched:
        print('  %d log entr%s did not match anything (see warnings above)'
              % (total_unmatched, 'y' if total_unmatched == 1 else 'ies'))


if __name__ == '__main__':
    main()
