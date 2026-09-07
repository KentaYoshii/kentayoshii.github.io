#!/usr/bin/env python3
"""Resolve book jackets and film posters at build time into docs/_data.

Two modes, and the distinction matters:

    python3 scripts/build_covers.py            # offline, no network at all
    python3 scripts/build_covers.py --fetch    # look up whatever is missing

The offline mode is what build.py and CI run. It reads the committed cache in
docs/_data/covers.json, writes a `cover` field onto every record in books.json
and movies.json, and touches the network never — so the build stays
deterministic and CI needs no API key. Anything not in the cache simply gets
no cover, and the page falls back to its placeholder glyph.

--fetch is the occasional manual pass that fills the cache in. Run it after
adding books or films, then commit covers.json along with the rest of _data.

Why do this at all, rather than in the browser as it used to be:

  - The TMDB key had to ship in the page source, because a static site has no
    backend to hide it behind.
  - Every visitor re-ran the same few hundred lookups, throttled four at a
    time behind an IntersectionObserver, with a localStorage cache to stop it
    happening again on the next visit. All of that is gone.
  - A lookup that fails now fails once, here, visibly in the output — instead
    of silently on someone's phone.

Books with an ISBN are free: Open Library serves a jacket straight from it, so
the URL is pure string construction and needs neither a request nor a cache
entry. Only ISBN-less books and films need looking up, which is why --fetch is
a much shorter run than the book count suggests.
"""

import argparse
import collections
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'docs', '_data')
CACHE_PATH = os.path.join(DATA, 'covers.json')

# Open Library builds a jacket URL from an ISBN with no search step. The
# default=false parameter makes it 404 on an unknown ISBN rather than serving
# a placeholder, so the page's <img> error handler can drop the image.
OPENLIBRARY_ISBN = 'https://covers.openlibrary.org/b/isbn/%s-M.jpg?default=false'
OPENLIBRARY_SEARCH = 'https://openlibrary.org/search.json?%s'
OPENLIBRARY_ID = 'https://covers.openlibrary.org/b/id/%s-M.jpg'
TMDB_SEARCH = 'https://api.themoviedb.org/3/search/%s?%s'
TMDB_IMAGE = 'https://image.tmdb.org/t/p/w200%s'

# Open Library asks crawlers to go slowly and to identify themselves.
USER_AGENT = 'kentayoshii.github.io cover build (github.com/KentaYoshii)'
REQUEST_PAUSE = 0.25
REQUEST_TIMEOUT = 15

# Write the cache back this often during --fetch, so a run interrupted after
# 200 lookups does not throw all 200 away.
CHECKPOINT_EVERY = 25


class LookupError_(Exception):
    """A request failed in a way that should stop the run rather than be
    recorded as 'this title has no cover'."""


def get_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode('utf-8'))


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def dump(name, payload):
    path = os.path.join(DATA, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write('\n')


def load_cache():
    """Cached lookups, keyed by kind. Missing or corrupt is not an error —
    the cache is derived data and a --fetch run rebuilds it."""
    try:
        with open(CACHE_PATH, encoding='utf-8') as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    return {
        'books': cache.get('books') or {},
        'movies': cache.get('movies') or {},
    }


def save_cache(cache):
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        # Sorted so the committed file has a stable order and diffs show only
        # genuinely new entries.
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')


# ---- keys -------------------------------------------------------------------

def book_key(book):
    """Cache key for a book that needs a search. Books with an ISBN never get
    here — their URL is built directly."""
    return ('%s|%s' % (book['title'], book.get('author') or '')).lower()


def movie_key(movie):
    """The raw log title, which is what the search is derived from. Two
    entries written the same way share one poster, which is correct."""
    return movie['title'].lower()


# ---- title parsing ----------------------------------------------------------

SERIES_MARK = re.compile(r'\(\s*tv series\s*\)|\bseason\s+\d+\b', re.I)
# A trailing '(1987)' disambiguates a remake from its original. The optional
# word covers the Wikipedia-style '(2024 film)', which the browser-side
# version of this could not parse and so searched for literally, finding
# nothing.
TRAILING_YEAR = re.compile(
    r'\(\s*(1[89]\d\d|20\d\d)(?:\s+(?:film|movie))?\s*\)\s*$', re.I)


def parse_movie_title(raw):
    """Split a log title into what TMDB should actually be asked.

    'Reacher Season 2 (TV Series)' -> searched in the TV catalogue as
    'Reacher'; 'The Count of Monte-Cristo (2024)' -> searched as a film with
    a release-year filter, so a remake does not collide with its original.
    """
    raw = (raw or '').strip()
    if not raw:
        return None

    is_series = bool(SERIES_MARK.search(raw))
    year_match = TRAILING_YEAR.search(raw)

    cleaned = TRAILING_YEAR.sub('', raw)
    cleaned = re.sub(r'\(\s*tv series\s*\)', '', cleaned, flags=re.I)
    cleaned = re.sub(r'\bseason\s+\d+\b', '', cleaned, flags=re.I)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()

    return {
        'title': cleaned or raw,
        'is_series': is_series,
        'year': year_match.group(1) if year_match else None,
    }


def fold(s):
    """Loose comparison form for 'is this the film we asked for'."""
    return re.sub(r'[^\w]+', '', (s or '').lower(), flags=re.UNICODE)


# ---- lookups ----------------------------------------------------------------

def fetch_book_cover(book):
    """Open Library search, for the books with no ISBN to go on."""
    def search(with_author):
        params = {'title': book['title'], 'limit': '1', 'fields': 'cover_i'}
        if with_author and book.get('author'):
            params['author'] = book['author']
        data = get_json(OPENLIBRARY_SEARCH % urllib.parse.urlencode(params))
        docs = (data or {}).get('docs') or []
        if docs and docs[0].get('cover_i'):
            return OPENLIBRARY_ID % docs[0]['cover_i']
        return None

    # Title+author is the precise query but fails whenever Open Library's
    # credited author differs from ours (translators, anthology editors); a
    # title-only search catches those.
    url = search(True)
    if url or not book.get('author'):
        return url
    time.sleep(REQUEST_PAUSE)
    return search(False)


def fetch_movie_cover(info, api_key):
    """TMDB search, mirroring the ordering the page used to do client-side."""
    def pick(results):
        # TMDB ranks by popularity, not title match, so a short generic title
        # can return an unrelated but busier film first. Prefer an exact hit.
        wanted = fold(info['title'])
        fallback = None
        for result in results or []:
            if not result.get('poster_path'):
                continue
            if fold(result.get('title') or result.get('name')) == wanted:
                return result
            if fallback is None:
                fallback = result
        return fallback

    def search(kind):
        params = {'api_key': api_key, 'query': info['title']}
        if info['year']:
            # TMDB names the release-year filter differently per catalogue.
            params['first_air_date_year' if kind == 'tv' else 'year'] = info['year']
        data = get_json(TMDB_SEARCH % (kind, urllib.parse.urlencode(params)))
        result = pick((data or {}).get('results'))
        return TMDB_IMAGE % result['poster_path'] if result else None

    # Anything marked as a series searches TV first, or a film false-positive
    # wins before the TV catalogue is ever tried.
    order = ('tv', 'movie') if info['is_series'] else ('movie', 'tv')
    for kind in order:
        url = search(kind)
        if url:
            return url
        time.sleep(REQUEST_PAUSE)
    return None


# ---- the two passes ---------------------------------------------------------

def wanted_keys(books, movies):
    """Every cache key the current data actually needs."""
    return (
        {book_key(b) for b in books if not b.get('isbn')},
        {movie_key(m) for m in movies},
    )


def resolve_missing(books, movies, cache, api_key, only=None):
    """The --fetch pass. Fills in cache entries that do not exist yet.

    A key already present is left alone even when its value is null: null
    means "looked this up and there is no cover", and re-running should not
    keep asking. Delete the entry to force a retry.

    `only` restricts the pass to 'books' or 'movies' — useful when one of the
    two APIs is unreachable, or when only one log has changed.
    """
    pending_books = []
    if only in (None, 'books'):
        pending_books = [b for b in books
                         if not b.get('isbn') and book_key(b) not in cache['books']]

    pending_movies = []
    if only in (None, 'movies'):
        seen = set()
        for movie in movies:
            key = movie_key(movie)
            if key in cache['movies'] or key in seen:
                continue
            seen.add(key)
            pending_movies.append(movie)

    if not pending_books and not pending_movies:
        print('  nothing to fetch; the cache already covers every entry')
        return 0

    done = 0

    if pending_books:
        print('  looking up %d book(s) with no ISBN' % len(pending_books))
        for book in pending_books:
            url = fetch_book_cover(book)
            cache['books'][book_key(book)] = url
            done += 1
            print('    %-46s %s' % (book['title'][:46], url or '(none)'))
            if done % CHECKPOINT_EVERY == 0:
                save_cache(cache)
            time.sleep(REQUEST_PAUSE)

    if pending_movies:
        if not api_key:
            print('  skipping %d film(s): TMDB_API_KEY is not set'
                  % len(pending_movies))
        else:
            print('  looking up %d film(s)' % len(pending_movies))
            for movie in pending_movies:
                info = parse_movie_title(movie['title'])
                url = fetch_movie_cover(info, api_key) if info else None
                cache['movies'][movie_key(movie)] = url
                done += 1
                print('    %-46s %s' % (movie['title'][:46], url or '(none)'))
                if done % CHECKPOINT_EVERY == 0:
                    save_cache(cache)
                time.sleep(REQUEST_PAUSE)

    save_cache(cache)
    return done


def apply_covers(books, movies, cache):
    """Write the `cover` field onto every record. Offline and deterministic:
    an ISBN becomes a URL by construction, everything else is a cache hit or
    nothing at all."""
    counts = collections.Counter()

    for book in books:
        if book.get('isbn'):
            book['cover'] = OPENLIBRARY_ISBN % urllib.parse.quote(book['isbn'])
            counts['book_isbn'] += 1
        else:
            url = cache['books'].get(book_key(book))
            book['cover'] = url
            counts['book_search' if url else 'book_missing'] += 1

    for movie in movies:
        url = cache['movies'].get(movie_key(movie))
        movie['cover'] = url
        counts['movie' if url else 'movie_missing'] += 1

    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--fetch', action='store_true',
        help='look up covers that are not cached yet (requires network, and '
             'TMDB_API_KEY for films)')
    parser.add_argument(
        '--only', choices=('books', 'movies'),
        help='restrict --fetch to one source, for when the other API is '
             'unreachable or only one log has changed')
    # build.py calls main() with no arguments; argparse would otherwise read
    # sys.argv and choke on another script's flags.
    args = parser.parse_args([] if argv is None else argv)

    books = load('books.json')
    movies = load('movies.json')
    cache = load_cache()

    if args.fetch:
        try:
            resolve_missing(books, movies, cache,
                            os.environ.get('TMDB_API_KEY', '').strip(),
                            only=args.only)
        except (urllib.error.URLError, OSError) as exc:
            # Whatever was resolved before the failure is already checkpointed.
            save_cache(cache)
            print('  fetch stopped: %s' % exc, file=sys.stderr)
            print('  cached results so far were kept; re-run to continue',
                  file=sys.stderr)
            return 1

    # Drop entries for books and films no longer in the logs, so the cache
    # does not accumulate forever.
    keep_books, keep_movies = wanted_keys(books, movies)
    dropped = ((len(cache['books']) - len(cache['books'].keys() & keep_books)) +
               (len(cache['movies']) - len(cache['movies'].keys() & keep_movies)))
    cache['books'] = {k: v for k, v in cache['books'].items() if k in keep_books}
    cache['movies'] = {k: v for k, v in cache['movies'].items() if k in keep_movies}

    counts = apply_covers(books, movies, cache)

    dump('books.json', books)
    dump('movies.json', movies)
    save_cache(cache)

    print('wrote covers -> %s' % os.path.relpath(CACHE_PATH, ROOT))
    print('  books: %d by isbn, %d by search, %d without'
          % (counts['book_isbn'], counts['book_search'], counts['book_missing']))
    print('  films: %d with a poster, %d without'
          % (counts['movie'], counts['movie_missing']))
    if dropped:
        print('  dropped %d stale cache entr%s'
              % (dropped, 'y' if dropped == 1 else 'ies'))
    missing = counts['book_missing'] + counts['movie_missing']
    if missing:
        print('  %d entr%s still unresolved — run with --fetch to look them up'
              % (missing, 'y' if missing == 1 else 'ies'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
