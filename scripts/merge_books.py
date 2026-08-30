#!/usr/bin/env python3
"""Merge the Goodreads export with the hand-written markdown book logs into
docs/_data/books.json, which the Books page renders from.

Run after dropping a fresh Goodreads export at the repo root:

    python3 scripts/merge_books.py

Why both sources:
  - Goodreads has more books (only its "read" shelf is used) and, crucially,
    ISBNs — which let the cover lookup hit Open Library directly instead of
    guessing from a title search.
  - docs/_logs/books.md is the only source of *when* a book was read;
    Goodreads' export has an empty "Date Read" column throughout. It stays in
    the repo as the year source and as a chronological archive.
"""

import collections
import csv
import difflib
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_PATH = os.path.join(ROOT, 'goodreads_library_export.csv')
LOG_PATH = os.path.join(ROOT, 'docs', '_logs', 'books.md')
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


def sort_title(t):
    """Titles file under their first significant word, so 'The Covenant of
    Water' sorts and groups under C."""
    return re.sub(r'^(the|a|an)\s+', '', nfkc(t).strip(), flags=re.I)


def letter_of(t):
    """Grouping bucket for the 'First letter' view. Anything not starting with
    a Latin letter (digits, Japanese titles) collects under '#'."""
    s = fold(sort_title(t)).upper()
    return s[0] if s and 'A' <= s[0] <= 'Z' else '#'


def strip_series(t):
    """Drop Goodreads' trailing series/romanization annotations:
    '1Q84 (1Q84, #1-3)' and '永遠の0 [Eien No Zero]'."""
    t = re.sub(r'\s*\([^()]*\)\s*$', '', t)
    t = re.sub(r'\s*\[[^\[\]]*\]\s*$', '', t)
    return t.strip()


# Goodreads appends '(Series Name, #3)' to titles in a series. The '#' is what
# distinguishes those from ordinary trailing parentheticals such as
# '君のクイズ (Japanese Edition)' or 'The Fall (Vintage International)'.
SERIES_RE = re.compile(r'\(([^()]*?),?\s*#([^()]*?)\)\s*$')

# A series represented by a single read book is not a series worth showing —
# it just puts 34 one-item sections in the list — so entries only keep their
# series once this many books from it have been read.
SERIES_MIN = 2


def parse_series(title):
    """('The Return of Sherlock Holmes (Sherlock Holmes, #6)')
        -> ('Sherlock Holmes', '6')."""
    m = SERIES_RE.search(nfkc(title).strip())
    if not m:
        return None, None
    name = squash(m.group(1))
    index = squash(m.group(2))
    return (name, index) if name else (None, None)


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
    # Goodreads titles a collection after its lead story plus a catch-all
    # ('The Dancing Girl of Izu and Other Stories'); the log uses just the
    # lead story. Indexing both sides under the short form bridges that.
    add(re.sub(r'\s+and other\s+\w+\s*$', '', base, flags=re.I))
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


# Pairs the normaliser cannot bridge on its own, mapping a title as written in
# the log to the title Goodreads files it under. Kept explicit rather than
# guessed at, since a wrong match silently attaches another book's ISBN, page
# count and cover.
ALIASES = {
    # Goodreads uses the short popular title.
    'The Strange Case of Dr. Jekyll and Mr. Hyde': 'Dr. Jekyll and Mr. Hyde',
    # Goodreads splits the novel into two volumes; the log records it once.
    # Matching volume 1 also unifies the author, whom Goodreads romanises.
    '俺たちの箱根駅伝': '俺たちの箱根駅伝 上',
}


def alias_keys(title):
    """Extra match keys for a log title with a known Goodreads counterpart."""
    target = ALIASES.get(squash(strip_series(nfkc(title))))
    return title_keys(target) if target else []


def as_int(v):
    v = (v or '').strip()
    m = re.match(r'^(-?\d+)(?:\.0+)?$', v)
    return int(m.group(1)) if m else None


def load_goodreads():
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    books = []
    for r in rows:
        if r.get('Exclusive Shelf', '').strip() != 'read':
            continue  # skip to-read / currently-reading
        series, series_index = parse_series(r['Title'])
        books.append({
            'title': strip_series(nfkc(r['Title'])),
            'author': squash(r['Author']),
            'isbn': clean_excel(r.get('ISBN13')) or clean_excel(r.get('ISBN')),
            'pages': as_int(r.get('Number of Pages')),
            # Original publication year, not this edition's reprint date, so
            # the classics read as old.
            'published': as_int(r.get('Original Publication Year')
                                or r.get('Year Published')),
            'series': series,
            'series_index': series_index,
            'keys': title_keys(r['Title']),
        })

    # Drop the series label from books whose series is only represented once.
    counts = collections.Counter(b['series'] for b in books if b['series'])
    for b in books:
        if b['series'] and counts[b['series']] < SERIES_MIN:
            b['series'] = None
            b['series_index'] = None

    return books, len(rows)


def load_markdown():
    """Read docs/_logs/books.md, where a '## <year>' heading dates everything
    beneath it and '## Undated' marks the pre-2024 backlog. Books are recorded
    at year granularity, so the '###' month subheadings are not parsed."""
    entries = []
    year = None
    for line in open(LOG_PATH, encoding='utf-8'):
        line = line.rstrip()
        head = re.match(r'^##\s+(.+?)\s*$', line)
        if head:
            label = head.group(1)
            year = label if re.fullmatch(r'\d{4}', label) else None
            continue
        m = re.match(r'^-\s+_(.+?)_\s*(?:by\s+)?(.*)$', line.strip())
        if not m:
            continue
        title, author = m.group(1).strip(), m.group(2).strip()
        if not author:
            continue
        entries.append({
            'title': squash(title),
            'author': squash(author),
            'year': year,
            'keys': sorted(set(title_keys(title)) | set(alias_keys(title))),
        })
    return entries


# A log entry this similar to a Goodreads title, by the same author, is almost
# certainly the same book with a typo or a title-form difference.
NEAR_TITLE = 0.72
NEAR_AUTHOR = 0.80


def report_near_misses(md_only, gr):
    """Warn about log entries that look like a Goodreads book the matcher
    missed, so a typo does not silently cost a book its ISBN and cover.

    The author is what keeps this quiet: 'Ford County' and 'Snow Country' are
    similar enough to trip the title test, but Grisham is not Kawabata.
    """
    hits = []
    for m in md_only:
        best = None
        for g in gr:
            ta = difflib.SequenceMatcher(None, keyify(m['title']),
                                         keyify(g['title'])).ratio()
            if ta < NEAR_TITLE:
                continue
            aa = difflib.SequenceMatcher(None, keyify(m['author']),
                                         keyify(g['author'])).ratio()
            if aa < NEAR_AUTHOR:
                continue
            if best is None or ta > best[0]:
                best = (ta, g)
        if best:
            hits.append((m, best[1], best[0]))

    if not hits:
        return
    print('\n  %d log entr%s look like an unmatched Goodreads book:'
          % (len(hits), 'y' if len(hits) == 1 else 'ies'))
    for m, g, ratio in sorted(hits, key=lambda h: -h[2]):
        print('    %-38s -> %-38s (%s, %.0f%%)'
              % (m['title'][:38], g['title'][:38], g['author'][:22], ratio * 100))
    print('    Fix the log title, or add a pair to ALIASES in this script.')


def report_duplicates(books):
    """Warn about entries that are probably the same work listed twice."""
    exact = collections.Counter((keyify(b['title']), keyify(b['author']))
                                for b in books)
    dupes = [k for k, n in exact.items() if n > 1]
    if dupes:
        print('\n  %d duplicate title+author pair(s):' % len(dupes))
        for b in books:
            if exact[(keyify(b['title']), keyify(b['author']))] > 1:
                print('    %-40s %s' % (b['title'][:40], b['author'][:24]))

    # One work split across volumes, or a set listed alongside its parts.
    stem = collections.defaultdict(list)
    for b in books:
        base = re.sub(r'\s*[上中下巻]\s*$|\s+(vol\.?|volume|part|book)\s*\d+\s*$',
                      '', b['title'], flags=re.I)
        stem[(keyify(base), keyify(b['author']))].append(b['title'])
    split = {k: v for k, v in stem.items() if len(v) > 1}
    if split:
        print('\n  %d work(s) listed as multiple volumes:' % len(split))
        for v in split.values():
            print('    %s' % ' | '.join(v))

    placeholder = [b for b in books
                   if re.search(r'\b(series|trilogy|collection|omnibus)\b',
                                b['title'], re.I)]
    if placeholder:
        print('\n  %d entr%s name a set rather than one book:'
              % (len(placeholder), 'y' if len(placeholder) == 1 else 'ies'))
        for b in placeholder:
            print('    %-40s %s' % (b['title'][:40], b['author'][:24]))


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
            'pages': g['pages'],
            'published': g['published'],
            'series': g['series'],
            'series_index': g['series_index'],
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
            'pages': None,
            'published': None,
            # Only Goodreads annotates series; a markdown-only book has no
            # source for it.
            'series': None,
            'series_index': None,
        })

    # The page's default view is an ungrouped A-Z list, so sort by title here
    # and let the client re-group without re-sorting.
    for b in books:
        b['letter'] = letter_of(b['title'])
    books.sort(key=lambda b: (keyify(sort_title(b['title'])), keyify(b['author'])))

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
    print('  with pages: %d | with pub year: %d'
          % (sum(1 for b in books if b['pages']),
             sum(1 for b in books if b['published'])))
    in_series = [b for b in books if b['series']]
    print('  in a series: %d across %d series (min %d books each)'
          % (len(in_series), len({b['series'] for b in in_series}), SERIES_MIN))

    report_near_misses(md_only, gr)
    report_duplicates(books)


if __name__ == '__main__':
    main()
