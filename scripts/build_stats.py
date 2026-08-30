#!/usr/bin/env python3
"""Derive docs/_data/stats.json from the generated books/movies data.

Run after the other two scripts (or just run scripts/build.py, which runs
all three in order):

    python3 scripts/build_stats.py

Computed here rather than in Liquid because medians, extremes and century
buckets are awkward to express as template filters, and doing it at build
time keeps the stats page free of client-side work.
"""

import collections
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'docs', '_data')

# How many covers the landing page's decorative band shows. Each one is an
# extra lazy image request, so keep it modest.
MOSAIC_COUNT = 36


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def century_label(year):
    """-750 -> '8th century BC'; 1975 -> '20th century'."""
    if year < 0:
        n = (-year - 1) // 100 + 1
        return '%s century BC' % ordinal(n)
    return '%s century' % ordinal((year - 1) // 100 + 1)


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return '%d%s' % (n, suffix)


def main():
    books = load('books.json')
    movies = load('movies.json')

    pages = [b['pages'] for b in books if b['pages']]
    pages.sort()
    published = [b for b in books if b['published'] is not None]
    by_author = collections.Counter(b['author'] for b in books)
    by_year = collections.Counter(b['year'] for b in books if b['year'])
    longest = max((b for b in books if b['pages']), key=lambda b: b['pages'])
    shortest = min((b for b in books if b['pages']), key=lambda b: b['pages'])
    oldest = min(published, key=lambda b: b['published'])
    newest = max(published, key=lambda b: b['published'])

    centuries = collections.Counter(century_label(b['published']) for b in published)

    # merge_books.py has already dropped series with only one book read, so
    # every series here has at least two.
    in_series = [b for b in books if b.get('series')]
    by_series = collections.Counter(b['series'] for b in in_series)

    # ISBNs for the landing page's decorative cover band. Books are sorted by
    # title, so take an even stride through them rather than the first N --
    # otherwise the band is forty books beginning with "A".
    with_isbn = [b['isbn'] for b in books if b['isbn']]
    step = max(1, len(with_isbn) // MOSAIC_COUNT)
    mosaic = with_isbn[::step][:MOSAIC_COUNT]

    movie_years = collections.Counter(m['year'] for m in movies)

    stats = {
        'books': {
            'total': len(books),
            'authors': len(by_author),
            'pages_total': sum(pages),
            # Liquid has no thousands-separator filter, so format here.
            'pages_total_pretty': '{:,}'.format(sum(pages)),
            'pages_median': pages[len(pages) // 2] if pages else None,
            'pages_counted': len(pages),
            'longest': {'title': longest['title'], 'author': longest['author'],
                        'pages': longest['pages']},
            'shortest': {'title': shortest['title'], 'author': shortest['author'],
                         'pages': shortest['pages']},
            'oldest': {'title': oldest['title'], 'author': oldest['author'],
                       'published': oldest['published']},
            'newest': {'title': newest['title'], 'author': newest['author'],
                       'published': newest['published']},
            'span_years': newest['published'] - oldest['published'],
            'span_years_pretty': '{:,}'.format(newest['published'] - oldest['published']),
            'top_authors': [{'name': n, 'count': c} for n, c in by_author.most_common(10)],
            'by_year': [{'year': y, 'count': by_year[y]} for y in sorted(by_year, reverse=True)],
            'dated': sum(by_year.values()),
            'centuries': [{'name': n, 'count': c} for n, c in
                          sorted(centuries.items(), key=lambda kv: -kv[1])[:6]],
            'mosaic': mosaic,
            'series_count': len(by_series),
            'in_series': len(in_series),
            'top_series': [{'name': n, 'count': c}
                           for n, c in by_series.most_common(8)],
        },
        'movies': {
            'total': len(movies),
            'by_year': [{'year': y, 'count': movie_years[y]}
                        for y in sorted(movie_years, reverse=True)],
        },
    }

    out = os.path.join(DATA, 'stats.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
        f.write('\n')

    b = stats['books']
    print('wrote stats -> %s' % os.path.relpath(out, ROOT))
    print('  %d books, %d authors, %s pages' % (b['total'], b['authors'], f"{b['pages_total']:,}"))
    print('  span %s -> %s (%d years)' % (b['oldest']['published'],
                                          b['newest']['published'], b['span_years']))
    print('  %d books across %d series' % (b['in_series'], b['series_count']))
    print('  %d movies/shows' % stats['movies']['total'])


if __name__ == '__main__':
    main()
