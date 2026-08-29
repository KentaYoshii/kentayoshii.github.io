#!/usr/bin/env python3
"""Flatten the markdown movie logs into docs/_data/movies.json.

Run after editing anything in docs/_posts/*movies*:

    python3 scripts/build_movies.py

The Movies page offers a "group by" control (none / year / first letter), and
Liquid cannot read the month headings out of a rendered post body, so the
posts are flattened into a data file here instead. The posts stay in the repo
as the source of truth — this only mirrors them.
"""

import glob
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
POSTS_GLOB = os.path.join(ROOT, 'docs', '_posts', '*movies*')
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
    for path in sorted(glob.glob(POSTS_GLOB)):
        year = re.search(r'(\d{4})-\d\d-\d\d', os.path.basename(path)).group(1)
        month = None
        for line in open(path, encoding='utf-8'):
            line = line.rstrip()
            head = re.match(r'^##\s+(.+?)\s*$', line)
            if head:
                month = head.group(1) if head.group(1).lower() in MONTH_NUM else None
                continue
            m = re.match(r'^-\s+(.+?)\s*$', line)
            if not m:
                continue
            title = re.sub(r'\s+', ' ', nfkc(m.group(1))).strip()
            if not title:
                continue
            items.append({
                'title': title,
                'year': year,
                'month': month,
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
