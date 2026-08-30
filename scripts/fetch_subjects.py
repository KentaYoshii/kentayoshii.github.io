"""Fetches Open Library subjects for every book and caches them on disk.

This is the ONLY script in the pipeline that touches the network, and it is
deliberately not part of build.py. CI re-runs the build and fails if
docs/_data changes, so a build that fetched live would go red whenever Open
Library's data moved under it, for reasons having nothing to do with the
commit. Instead this writes scripts/subject_cache.json, that file is committed,
and merge_books.py reads it offline.

Usage:

    python3 scripts/fetch_subjects.py            # fetch anything not cached
    python3 scripts/fetch_subjects.py --refresh  # re-fetch everything
    python3 scripts/fetch_subjects.py --report   # no network; summarise cache
    python3 scripts/fetch_subjects.py --limit 20 # try a small batch first

Run it after adding books, then commit the cache alongside docs/_data.
"""

import argparse
import collections
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BOOKS_PATH = os.path.join(ROOT, 'docs', '_data', 'books.json')
CACHE_PATH = os.path.join(HERE, 'subject_cache.json')

# Open Library asks that scripts identify themselves so they can get in touch
# rather than simply blocking. https://openlibrary.org/developers/api
USER_AGENT = 'kentayoshii.github.io book-log/1.0 (https://kentayoshii.github.io)'

# The books API takes many bibkeys at once, which turns ~420 lookups into ~11
# requests. Kept well under any URL length limit.
BATCH = 40
DELAY = 1.0          # seconds between requests
TIMEOUT = 30
RETRIES = 3
MAX_CONSECUTIVE_FAILURES = 3


def cache_key(book):
    """Stable identity for a book across runs. ISBN when there is one; title
    and author otherwise, which is all a book from the markdown log has."""
    if book.get('isbn'):
        return 'isbn:' + book['isbn']
    return 'ta:%s|%s' % (book.get('title', '').lower().strip(),
                         book.get('author', '').lower().strip())


def get_json(url):
    """Parsed JSON, or None if the request could not be completed.

    None means "no answer" and must not be confused with an answer of "this
    book has no subjects" — caching the former would permanently skip books
    that a later, working run could have resolved. A 404 is a real answer and
    comes back as an empty dict.
    """
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
    })
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            if e.code != 429 and e.code < 500:
                print('  ! HTTP %d %s' % (e.code, url), file=sys.stderr)
                return None
            wait = DELAY * (2 ** attempt) * 5
            print('  . HTTP %d, retrying in %.0fs' % (e.code, wait), file=sys.stderr)
            time.sleep(wait)
        except Exception as e:                      # network hiccup, timeout
            wait = DELAY * (2 ** attempt) * 2
            print('  . %s, retrying in %.0fs' % (type(e).__name__, wait), file=sys.stderr)
            time.sleep(wait)
    print('  ! gave up on %s' % url, file=sys.stderr)
    return None


def fetch_by_isbn(isbns):
    """One request for up to BATCH ISBNs. Returns {isbn: [subject, ...]}."""
    bibkeys = ','.join('ISBN:' + i for i in isbns)
    url = ('https://openlibrary.org/api/books?bibkeys=%s&format=json&jscmd=data'
           % urllib.parse.quote(bibkeys, safe=':,'))
    data = get_json(url)
    if data is None:
        return None                     # request failed; nothing learned
    out = {}
    for isbn in isbns:
        entry = data.get('ISBN:' + isbn)
        if not entry:
            continue
        # jscmd=data returns subjects as [{name, url}, ...].
        out[isbn] = [s.get('name', '') for s in entry.get('subjects', [])]
    return out


def fetch_by_search(title, author):
    """Fallback for the books with no ISBN. One request, best single match."""
    params = {'title': title, 'limit': '1', 'fields': 'subject'}
    if author:
        params['author'] = author
    url = 'https://openlibrary.org/search.json?' + urllib.parse.urlencode(params)
    data = get_json(url)
    if data is None:
        return None                     # request failed; nothing learned
    docs = data.get('docs') or []
    if not docs:
        return []
    # The subject list on a search result runs to hundreds of entries for a
    # well-known book; the head is the useful part and the tail is noise.
    return (docs[0].get('subject') or [])[:40]


def load_cache():
    if not os.path.exists(CACHE_PATH):
        return {}
    with open(CACHE_PATH, encoding='utf-8') as f:
        return json.load(f)


def save_cache(cache):
    # Never leave an empty cache behind: a run that learned nothing (blocked
    # network, immediate abort) should not create a file to be committed.
    if not cache:
        return
    # sort_keys so the committed file has a readable diff when books are added
    # and does not churn on dict ordering.
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')


def report(cache, books):
    counts = collections.Counter()
    for entry in cache.values():
        for s in entry.get('subjects', []):
            counts[s] += 1

    have = sum(1 for e in cache.values() if e.get('subjects'))
    print('cached: %d of %d books (%d with subjects, %d known-empty)'
          % (len(cache), len(books), have, len(cache) - have))
    print('distinct raw subjects: %d' % len(counts))
    print('\nmost common raw subjects:')
    for name, n in counts.most_common(60):
        print('  %4d  %s' % (n, name))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--refresh', action='store_true',
                    help='re-fetch books already in the cache')
    ap.add_argument('--report', action='store_true',
                    help='summarise the cache without fetching anything')
    ap.add_argument('--limit', type=int, default=0,
                    help='stop after this many books (for a trial run)')
    ap.add_argument('--delay', type=float, default=DELAY,
                    help='seconds between requests (default %.1f)' % DELAY)
    args = ap.parse_args()

    with open(BOOKS_PATH, encoding='utf-8') as f:
        books = json.load(f)

    cache = load_cache()

    if args.report:
        report(cache, books)
        return

    todo = [b for b in books if args.refresh or cache_key(b) not in cache]
    if args.limit:
        todo = todo[:args.limit]

    if not todo:
        print('nothing to fetch — %d books already cached' % len(cache))
        report(cache, books)
        return

    with_isbn = [b for b in todo if b.get('isbn')]
    without = [b for b in todo if not b.get('isbn')]
    batches = (len(with_isbn) + BATCH - 1) // BATCH
    print('fetching %d book(s): %d by ISBN in %d batch(es), %d by search'
          % (len(todo), len(with_isbn), batches, len(without)))
    print('roughly %.0f seconds at %.1fs between requests'
          % ((batches + len(without)) * args.delay, args.delay))

    # Write the cache as we go. A run interrupted halfway then costs only the
    # requests it had not made yet, which matters at one request per second.
    # A run against a blocked network or a rate-limiting server learns nothing
    # and should stop rather than grind through every batch. Consecutive, not
    # total: the occasional failure among successes is not a reason to quit.
    misses = 0

    try:
        for i in range(0, len(with_isbn), BATCH):
            chunk = with_isbn[i:i + BATCH]
            found = fetch_by_isbn([b['isbn'] for b in chunk])
            if found is None:
                misses += 1
                print('  isbn batch %d/%d: request failed, not cached'
                      % (i // BATCH + 1, batches))
                if misses >= MAX_CONSECUTIVE_FAILURES:
                    print('\n%d requests in a row failed — stopping. Nothing was\n'
                          'cached for them, so re-running picks up where this left off.'
                          % misses, file=sys.stderr)
                    break
                time.sleep(args.delay)
                continue
            misses = 0
            for b in chunk:
                cache[cache_key(b)] = {
                    'title': b['title'],
                    'subjects': found.get(b['isbn'], []),
                    'source': 'isbn',
                }
            hits = sum(1 for b in chunk if found.get(b['isbn']))
            print('  isbn batch %d/%d: %d/%d with subjects'
                  % (i // BATCH + 1, batches, hits, len(chunk)))
            save_cache(cache)
            time.sleep(args.delay)

        for n, b in enumerate(without, 1):
            if misses >= MAX_CONSECUTIVE_FAILURES:
                break                   # the ISBN phase already gave up
            subjects = fetch_by_search(b['title'], b.get('author'))
            if subjects is None:
                misses += 1
                print('  search %d/%d: request failed, not cached' % (n, len(without)))
                if misses >= MAX_CONSECUTIVE_FAILURES:
                    print('\n%d requests in a row failed — stopping.' % misses,
                          file=sys.stderr)
                    break
                time.sleep(args.delay)
                continue
            misses = 0
            cache[cache_key(b)] = {
                'title': b['title'],
                'subjects': subjects,
                'source': 'search',
            }
            print('  search %d/%d: %-40.40s %d subject(s)'
                  % (n, len(without), b['title'], len(subjects)))
            save_cache(cache)
            time.sleep(args.delay)
    except KeyboardInterrupt:
        save_cache(cache)
        print('\ninterrupted — cache saved with %d entries' % len(cache))
        return

    save_cache(cache)
    if not cache:
        print('\nnothing was cached — every request failed. Check network access '
              'to openlibrary.org.', file=sys.stderr)
        return
    print('\nwrote %s' % os.path.relpath(CACHE_PATH, ROOT))
    report(cache, books)


if __name__ == '__main__':
    main()
