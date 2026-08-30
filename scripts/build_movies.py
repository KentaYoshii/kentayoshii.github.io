#!/usr/bin/env python3
"""Flatten docs/_logs/movies.md into docs/_data/movies.json.

Run after editing the log:

    python3 scripts/build_movies.py

The Movies page offers a "group by" control (none / year / first letter), and
Liquid cannot read the month headings out of a markdown body, so the log is
flattened into a data file here instead. The log stays in the repo as the
source of truth — this only mirrors it.
"""

import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOG_PATH = os.path.join(ROOT, 'docs', '_logs', 'movies.md')
OUT_PATH = os.path.join(ROOT, 'docs', '_data', 'movies.json')

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
MONTH_NUM = {m.lower(): i + 1 for i, m in enumerate(MONTHS)}


def nfkc(s):
    return unicodedata.normalize('NFKC', s or '')


def fold(s):
    out = []
    for c in unicodedata.normalize('NFKD', s):
        if unicodedata.combining(c):
            if c in ('゙', '゚'):
                out.append(c)
            continue
        out.append(c)
    return unicodedata.normalize('NFC', ''.join(out))


def keyify(s):
    return re.sub(r'[^\w]+', '', fold(nfkc(s)).lower(), flags=re.UNICODE)


def sort_title(t):
    return re.sub(r'^(the|a|an)\s+', '', nfkc(t).strip(), flags=re.I)


def letter_of(t):
    s = fold(sort_title(t)).upper()
    return s[0] if s and 'A' <= s[0] <= 'Z' else '#'


def main():
    items = []
    year = None
    month = None
    # '## 2025' opens a year, '### January' a month within it. A new year
    # clears the month so an entry cannot inherit one across the boundary.
    for line in open(LOG_PATH, encoding='utf-8'):
        line = line.rstrip()
        head = re.match(r'^##\s+(.+?)\s*$', line)
        if head:
            label = head.group(1)
            year = label if re.fullmatch(r'\d{4}', label) else None
            month = None
            continue
        sub = re.match(r'^###\s+(.+?)\s*$', line)
        if sub:
            month = sub.group(1) if sub.group(1).lower() in MONTH_NUM else None
            continue
        m = re.match(r'^-\s+(.+?)\s*$', line)
        if not m or year is None:
            continue
        title = re.sub(r'\s+', ' ', nfkc(m.group(1))).strip()
        if not title:
            continue
        items.append({
            'title': title,
            'year': year,
            'month': month,
            # Sortable stamp for the "date watched" ordering; entries with
            # no month heading sort to the start of their year.
            'date': '%s-%02d' % (year, MONTH_NUM.get((month or '').lower(), 0)),
            'letter': letter_of(title),
        })

    items.sort(key=lambda i: keyify(sort_title(i['title'])))

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
        f.write('\n')

    years = sorted({i['year'] for i in items})
    print('wrote %d movies/shows (%s) -> %s'
          % (len(items), ', '.join(years), os.path.relpath(OUT_PATH, ROOT)))
    print('  with month: %d' % sum(1 for i in items if i['month']))


if __name__ == '__main__':
    main()
