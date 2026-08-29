#!/usr/bin/env python3
"""Merge the Goodreads export with the hand-written markdown book logs into
docs/_data/books.json, which the Books page renders from.

Run after dropping a fresh Goodreads export at the repo root:

    python3 scripts/merge_books.py

Why both sources:
  - Goodreads has more books (only its "read" shelf is used) and, crucially,
    ISBNs — which let the cover lookup hit Open Library directly instead of
    guessing from a title search.
  - The markdown posts are the only source of *when* a book was read;
    Goodreads' export has an empty "Date Read" column throughout. They stay in
    the repo as the year source and as a chronological archive.
"""

import csv
import glob
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_PATH = os.path.join(ROOT, 'goodreads_library_export.csv')
POSTS_GLOB = os.path.join(ROOT, 'docs', '_posts', '*books*')
OUT_PATH = os.path.join(ROOT, 'docs', '_data', 'books.json')


def clean_excel(v):
    """Goodreads wraps ISBNs as ="0525555366" for Excel's benefit."""
    if not v:
        return ''
    m = re.match(r'^="(.*)"$', v.strip())
    return (m.group(1) if m else v).strip()


def nfkc(s):
    return unicodedata.normalize('NFKC', s or '')


def squash(s):
    """Collapse whitespace; Goodreads emits names like 'John  Green'."""
    return re.sub(r'\s+', ' ', nfkc(s)).strip()


def fold(s):
    """Strip Latin diacritics (Bronte/Brontë) while preserving Japanese voiced
    marks, so が does not collapse into か."""
    out = []
    for c in unicodedata.normalize('NFKD', s):
        if unicodedata.combining(c):
            if c in ('゙', '゚'):
                out.append(c)
            continue
        out.append(c)
    return unicodedata.normalize('NFC', ''.join(out))


def keyify(s):
    """Match key: keep letters/digits of any script (so CJK titles survive),
    drop punctuation, spacing, case and Latin accents."""
    return re.sub(r'[^\w]+', '', fold(nfkc(s)).lower(), flags=re.UNICODE)


def strip_series(t):
    """Drop Goodreads' trailing series/romanization annotations:
    '1Q84 (1Q84, #1-3)' and '永遠の0 [Eien No Zero]'."""
    t = re.sub(r'\s*\([^()]*\)\s*$', '', t)
    t = re.sub(r'\s*\[[^\[\]]*\]\s*$', '', t)
    return t.strip()


def title_keys(t):
    base = strip_series(nfkc(t))
    keys = set()

    def add(x):
        x = re.sub(r'\s+part\s+(\d+|one|two|three|four|five)\s*$', '',
                   x.strip(), flags=re.I)
        if not x:
            return
        for variant in (x, re.sub(r'^(the|a|an)\s+', '', x, flags=re.I)):
            k = keyify(variant)
            if k:
                keys.add(k)

    add(base)
    # Goodreads keeps subtitles ('Sapiens: A Brief History of Humankind',
    # 'Moby-Dick; or, The Whale') where the markdown uses the short title.
    for sep in (':', ';'):
        if sep in base:
            add(base.split(sep, 1)[0])
    # And the reverse: markdown writes 'Theodore Boone: The Abduction' while
    # Goodreads has 'The Abduction (Theodore Boone, #2)'.
    if ':' in base:
        add(base.split(':', 1)[1])
    # Sorted, not a set: an entry can match several records, and which one
    # wins must not depend on Python's per-process string hash seed, or the
    # generated file churns between runs.
    return sorted(keys)


def load_goodreads():
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    books = []
    for r in rows:
        if r.get('Exclusive Shelf', '').strip() != 'read':
            continue  # skip to-read / currently-reading
        books.append({
            'title': strip_series(nfkc(r['Title'])),
            'author': squash(r['Author']),
            'isbn': clean_excel(r.get('ISBN13')) or clean_excel(r.get('ISBN')),
            'keys': title_keys(r['Title']),
        })
    return books, len(rows)


def load_markdown():
    entries = []
    for path in sorted(glob.glob(POSTS_GLOB)):
        year = re.search(r'(\d{4})-\d\d-\d\d', os.path.basename(path)).group(1)
        text = open(path, encoding='utf-8').read()
        undated = bool(re.search(r'^undated:\s*true', text, re.M))
        for line in text.splitlines():
            m = re.match(r'^-\s+_(.+?)_\s*(?:by\s+)?(.*)$', line.strip())
            if not m:
                continue
            title, author = m.group(1).strip(), m.group(2).strip()
            if not author:
                continue
            entries.append({
                'title': squash(title),
                'author': squash(author),
                'year': None if undated else year,
                'keys': title_keys(title),
            })
    return entries


def main():
    gr, total_rows = load_goodreads()
    md = load_markdown()

    gr_index = {}
    for g in gr:
        for k in g['keys']:
            gr_index.setdefault(k, g)

    # Pass 1: match markdown entries to Goodreads, and learn how each author's
    # name is spelled on each side so the two spellings don't split into
    # separate sections on the page.
    # Seed with every Goodreads spelling, so a markdown-only book whose author
    # also appears in Goodreads ('JRR Tolkien' vs 'J.R.R. Tolkien') still lands
    # in that author's section rather than starting a near-duplicate one.
    author_canon = {}
    for g in gr:
        author_canon.setdefault(keyify(g['author']), g['author'])

    matches = {}
    md_only = []
    for m in md:
        hit = next((gr_index[k] for k in m['keys'] if k in gr_index), None)
        if hit is None:
            md_only.append(m)
            continue
        matches.setdefault(id(hit), []).append(m)
        author_canon[keyify(m['author'])] = hit['author']

    def canon_author(name):
        return author_canon.get(keyify(name), name)

    def pick_year(entries):
        years = sorted(e['year'] for e in entries if e['year'])
        return years[0] if years else None

    def pick_title(g, md_hits):
        """Prefer the markdown title, which is the short curated form
        ('Sapiens' rather than 'Sapiens: A Brief History of Humankind'), but
        defer to Goodreads in two cases."""
        if not md_hits:
            return g['title']
        titles = {m['title'] for m in md_hits}
        # Several markdown rows collapsed onto one work (a novel read in two
        # sittings: 'Shogun Part 1' + 'Shogun Part 2'), so neither label fits
        # the merged entry — use the canonical one.
        if len(titles) > 1:
            return g['title']
        md_title = md_hits[0]['title']
        # Same title, differing only in case/accents/punctuation ('King rat'
        # vs 'King Rat') — take Goodreads' canonical form.
        if keyify(md_title) == keyify(g['title']):
            return g['title']
        return md_title

    books = []
    for g in gr:
        md_hits = matches.get(id(g), [])
        books.append({
            'title': pick_title(g, md_hits),
            'author': g['author'],
            'isbn': g['isbn'],
            'year': pick_year(md_hits),
        })

    seen = set()
    for m in md_only:
        k = tuple(sorted(m['keys']))
        if k in seen:
            continue  # markdown lists a few books twice
        seen.add(k)
        books.append({
            'title': m['title'],
            'author': canon_author(m['author']),
            'isbn': '',
            'year': m['year'],
        })

    books.sort(key=lambda b: (keyify(b['author']), keyify(b['title'])))

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(books, f, ensure_ascii=False, indent=1)
        f.write('\n')

    authors = {b['author'] for b in books}
    print('goodreads rows: %d (read: %d)' % (total_rows, len(gr)))
    print('markdown entries: %d (matched: %d, md-only: %d)'
          % (len(md), len(md) - len(md_only), len(md_only)))
    print('wrote %d books by %d authors -> %s'
          % (len(books), len(authors), os.path.relpath(OUT_PATH, ROOT)))
    print('  with isbn: %d' % sum(1 for b in books if b['isbn']))
    print('  with year: %d' % sum(1 for b in books if b['year']))


if __name__ == '__main__':
    main()
