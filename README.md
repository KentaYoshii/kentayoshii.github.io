# Kenta's Log

A personal log of books read, movies/shows watched, national parks visited,
and dev notes. Live at <https://kentayoshii.github.io>.

Static [Jekyll](https://jekyllrb.com/) site using the `minima` theme, published
by GitHub Pages from the **`gh-pages` branch, `/docs` folder**. Pushing to
`gh-pages` deploys. A CI workflow checks each push but does not gate the
deploy — see [CI](#ci).

## Layout

```
docs/                     Jekyll site root
  _data/books.json        generated — do not edit by hand
  _data/movies.json       generated — do not edit by hand
  _data/stats.json        generated — do not edit by hand
  _data/travel.json       generated — do not edit by hand
  _logs/books.md          hand-written reading log (source of truth)
  _logs/movies.md         hand-written watch log (source of truth)
  _logs/travel.md         hand-written travel log (source of truth)
  _posts/                 blog posts only (`categories: posts`)
  books.markdown          renders _data/books.json
  movies.markdown         renders _data/movies.json
  travel.markdown         renders _data/travel.json
  stats.markdown          renders _data/stats.json
  posts.markdown          lists posts filed under `categories: posts`
  404.html                served by GitHub Pages for any unmatched path
  dev/vim-tips.markdown   dev notes, edited directly
  assets/js/main.js       search, grouping, cover art, dark mode
  assets/main.scss        theme
scripts/
  build.py                runs everything below, in order — the usual entry point
  merge_books.py          builds _data/books.json
  build_movies.py         builds _data/movies.json
  build_stats.py          builds _data/stats.json (reads the other two)
  build_images.py         draws the favicon and social card from books.json
  build_travel.py         builds _data/travel.json
  national_parks.py       fixed reference list of all 63 US National Parks
goodreads_library_export.csv   latest Goodreads export
```

The `_data/*.json` files are **generated**. Editing them directly works until
the next regeneration overwrites it — always edit the source and re-run the
build. When in doubt just run everything:

```sh
python3 scripts/build.py
```

`build_stats.py` reads the output of the other two, so if you run them
individually, run it last.

## Adding books

Books come from the union of two sources: the Goodreads export (more books,
and ISBNs) and the markdown logs (the only source of *when* a book was read —
Goodreads' export ships an empty `Date Read` column).

**Normal case — you've been logging on Goodreads:**

1. On Goodreads: *My Books → Import and Export → Export Library*, wait for the
   file, download it.
2. Save it over `goodreads_library_export.csv` at the repo root, keeping the
   name.
3. Regenerate and commit:

   ```sh
   python3 scripts/build.py
   git add goodreads_library_export.csv docs/_data
   git commit -m "Update books" && git push origin gh-pages
   ```

Only the `read` shelf is used; `to-read` and `currently-reading` are ignored.

**To record the year a book was read**, add it to `docs/_logs/books.md` under
the right `## <year>` heading, then re-run the script:

```markdown
## 2026
### March
- _Title_ by Author Name
```

The `## <year>` heading is what dates the entry. The `###` month subheadings
are for reading only — books are recorded at year granularity, so the month is
not parsed. Entries under `## Undated` (the pre-2024 backlog) deliberately
show no year.

### How the merge works

`merge_books.py` matches the two sources on a normalised title, which has to
absorb a fair amount of drift:

- Goodreads keeps subtitles and series suffixes — `Sapiens: A Brief History of
  Humankind`, `1Q84 (1Q84, #1-3)`, `The Abduction (Theodore Boone, #2)`
- romanisation brackets — `永遠の0 [Eien No Zero]`
- full-width digits, Latin diacritics (`Shōgun` vs `Shogun`), `Part 1`/`Part 2`
  splits of one novel

Where the two disagree:

- **Author** — Goodreads' spelling wins (`Natsume Sōseki`, `Brontë`), and the
  markdown variant is aliased onto it so one author never splits into two
  sections.
- **Title** — the markdown's shorter form wins (`Sapiens`, not the subtitled
  version), except when several markdown rows collapse onto one work or the
  two differ only by case/accents, where Goodreads' canonical form is used.

A title typo in the markdown silently prevents a match, which costs that book
its ISBN, page count, publication year and cover. `merge_books.py` warns about
this rather than leaving you to notice:

- **near misses** — a log entry whose title closely resembles a Goodreads one
  *by the same author*. The author check is what keeps it quiet about genuine
  coincidences like `Ford County` (Grisham) vs `Snow Country` (Kawabata).
- **duplicates** — the same title and author twice, one work listed as
  separate volumes, or an entry naming a set (`Harry Potter series`) rather
  than a book.

Warnings do not fail the build. Fix the log title, or if the two titles are
legitimately different — Goodreads using a short form, or splitting a novel
into volumes — add the pair to `ALIASES` in the script.

### Series

The same `(Series Name, #3)` suffix that the title matcher strips is also
captured, giving the Books page its "group by series" view and the stats page
its series chart. Two things to know:

- A series is only kept once **two or more** of its books have been read
  (`SERIES_MIN` in `merge_books.py`). Otherwise the 34 series represented by a
  single book each would add 34 one-item sections to the page.
- Series come from Goodreads only, so a markdown-only book never has one.

Grouping by series lists each section in publication order — `#1`, `#2`, … —
which is why the sort control greys out in that mode. Books in no series
collect in a `Standalone` section at the end.

## Adding movies and shows

Edit `docs/_logs/movies.md`, under the right `## <year>` and `### <Month>`
headings:

```markdown
## 2026
### June
- The Accountant 2
- Reacher Season 2 (TV Series)
```

Then regenerate and commit:

```sh
python3 scripts/build.py
git add docs/_logs docs/_data
git commit -m "Update movies" && git push origin gh-pages
```

The log remains the source of truth; the data file exists only because Liquid
cannot read the month headings out of a markdown body. **Editing the log
without re-running the script leaves the site showing stale data** — CI
catches this.

Mark TV entries with `(TV Series)` or `Season N` — the cover lookup uses that
to search TMDB's TV catalogue first, which otherwise returns a wrong film.

To separate a remake from its original, put the release year in the title:

```markdown
- The Running Man (2025)
- The Running Man (1987)
```

The lookup strips a trailing `(YYYY)` off the search text and passes it to
TMDB as a year filter, and includes it in the cover cache key — without it the
two would share one cached poster.

The year is also the fix when a short, common title fetches the wrong poster
(`Blade`, `Unstoppable`). TMDB ranks by popularity rather than title match, so
the lookup prefers a result whose title is exactly what was asked for before
falling back to the most popular one — but a year is still the reliable
disambiguator.

For a show, prefer one `Title (TV Series)` entry over one row per season.

## Travel

`docs/_logs/travel.md` groups entries by `## <category>` then `### <year>`,
currently just `## US National Parks`:

```markdown
## US National Parks

### 2026
- Yosemite
- Grand Teton
```

Then regenerate and commit:

```sh
python3 scripts/build_travel.py
git add docs/_logs/travel.md docs/_data/travel.json
git commit -m "Add a park visit" && git push origin gh-pages
```

Each category is a checklist against a known, finite universe — different
from Books and Movies, which only ever grow. `scripts/national_parks.py`
holds the fixed list of all 63 US National Parks (the NPS's "National Park"
designation specifically — not monuments, preserves, or historic sites), and
`build_travel.py` cross-references the log against it so the page can show
what's *left*, not just what's done. That reference list is not something
you log — it changes only when the NPS designates a new park (most recently
New River Gorge, in 2020) — so double check it against nps.gov if the
checklist ever looks short one.

A log entry is matched to an item by a normalised name comparison that also
tries prefixes in either direction (`Guadalupe` finds `Guadalupe Mountains`,
`Rocky Mountains` finds `Rocky Mountain`) and strips accents (`Haleakala`
finds `Haleakalā`). A name that changes more than that — `Hawaiian Volcanoes`
for `Hawaiʻi Volcanoes` — needs an entry in `ALIASES` at the bottom of
`national_parks.py`. An entry that matches nothing prints a warning rather
than silently vanishing from the count, the same principle as
`merge_books.py`'s near-miss detector.

### Adding another checklist

`build_travel.py`'s `CHECKLISTS` list is a registry of `(log heading, json
key, reference module)`. Adding a Countries checklist, say, needs three
things and no changes to the matching or page-rendering logic:

1. A reference module shaped like `national_parks.py` — `ITEMS`, a list of
   `(name, subtitle)` tuples (country, continent, say), plus an optional
   `ALIASES`.
2. An entry in `CHECKLISTS`.
3. A `## Countries` section in `travel.md` using that exact heading text.

`docs/travel.markdown` loops over whatever categories `travel.json` actually
contains, so a new checklist appears on the page automatically — nothing
there needs to change. A `## <heading>` in the log with no matching entry in
`CHECKLISTS` prints a warning rather than silently being dropped.

## Writing a post

`/posts/` lists anything in `_posts` filed under `categories: posts`. That
folder now holds nothing but real writing — the book and movie logs moved to
`_logs/`. No build step — Jekyll picks it up directly.

```markdown
---
layout: post
title: "Some title"
categories: posts
---

Body goes here.
```

Filenames are unconstrained: the generator scripts read `_logs/books.md` and
`_logs/movies.md` by exact path, so a post can be named anything.

## Stats page

`/stats/` is rendered entirely from `_data/stats.json` — no client-side work.
Page counts and publication years come from the Goodreads export (532 and 536
of 563 books respectively), so the totals are "across the books we have data
for", not the whole shelf. Ratings are deliberately absent: every row in the
export has `My Rating: 0`, so there is nothing to show until books get rated
on Goodreads.

## Design notes

A few pieces that are not obvious from the markup:

- **Sticky controls** — `.collection-header` sticks to the top of the Books and
  Movies pages. `main.js` measures its height into a `--sticky-h` custom
  property, which `.year-block`'s `scroll-margin-top` subtracts so a jump
  lands below the bar rather than behind it.
- **Jump rail** — rebuilt after every filter, so searching narrows it in step
  with the list. Twelve sections or fewer are listed by name (years); above
  that it collapses to initials, with non-Latin under `#`.
- **Cover shimmer** — keyed off `.is-settled`, which `applyCover` adds however
  the lookup ends. A miss has to settle too, or the placeholder would animate
  forever on the ~150 books with no cover.
- **Status strip** — a muted line under the header on every page: the
  author's local time, current weather, and a quote, inserted by
  `initStatusStrip()` rather than templated, so nothing else needed to
  change. Fixed to New York regardless of visitor — this is the author's
  time and weather, not a geolocation feature — via `STATUS_LAT` /
  `STATUS_LON` / `STATUS_TIMEZONE` at the top of that function in `main.js`.
  Weather comes from Open-Meteo, chosen because it needs no key and no
  attribution; the quote comes from a short hand-picked `QUOTES` list in the
  same function rather than a live "inspirational quote" API — the standard
  one for this (`api.quotable.io`) turned out to be down entirely while
  building this, and a couple of others were unreachable in testing too. A
  fixed list can't go dark the way a free third-party API can. It changes
  once a day rather than on every reload, keyed off a day number computed in
  `STATUS_TIMEZONE` so it flips at NYC midnight along with the rest of the
  strip, not at an hour that depends on the visitor's own timezone. Each
  part degrades independently: the clock needs nothing to render, the
  weather text simply never appears on a failed fetch, and the quote needs
  no network at all.
- **Landing page mosaic** — 24 slots chosen at build time by striding through
  the title-sorted shelf and watch list (`MOSAIC_COUNT` / `MOSAIC_MOVIES` in
  `build_stats.py`), so it is not 24 titles beginning with "A". Book jackets
  resolve straight from an ISBN and are plain `<img>` tags; TMDB has no
  title-addressable poster URL, so film slots start `hidden` and `main.js`
  fills them from the shared cover cache. With no JavaScript the band is just
  books. Jacket URLs carry `?default=false` so Open Library 404s on a missing
  cover instead of serving a blank, and `main.js` drops anything that fails or
  comes back under 10px wide — but only after a real `load` or `error` event.
  A `loading="lazy"` image whose load is still deferred can report
  `complete === true` with `naturalWidth` 0, so testing `complete` alone
  deletes every jacket before it loads. The jackets are therefore **not** lazy:
  the band clips horizontally, so a lazy image outside the clipped region never
  enters the viewport, never loads at all, and stays an empty slot forever.
  Film slots parse `(TV Series)` and a trailing `(YYYY)` out of the title the
  same way the Movies page does. Decorative and `aria-hidden`.
- **Mosaic drift** — the band scrolls in a seamless loop. Three nested
  elements, each with one job: `.cover-mosaic` clips and fades, `.mosaic-track`
  moves, `.mosaic-set` is one copy of the slots. `main.js` clones the set and
  shifts the track by exactly one copy's width plus one gap, so copy two lands
  where copy one began. Four things it depends on:
  - The track and set gaps must stay equal, or the shift is off by the
    difference and the loop jumps once a cycle.
  - Measuring waits until every slot has settled. Jackets are still being
    dropped and posters inserted before then, and a width measured mid-flight
    misaligns the loop permanently. An 8s timeout keeps one hung request from
    pinning the band still.
  - The band is centred when static but anchors left once it moves. Centring
    overflows both sides equally, which leaves the second copy half a window
    short and blanks the right-hand side at the end of every cycle.
  - Speed is fixed in px/s (`MOSAIC_SPEED`) and the duration derived from the
    measured width, so the pace is the same however many covers survive.

  Under `prefers-reduced-motion` none of it runs and the static band stays.
  Raising `MOSAIC_COUNT` lengthens the loop in proportion — at 24 slots it is
  a little over a minute.
- **Spine wall** — rendered in Liquid from `_data/books.json`, no extra data:
  width is `pages / 40` and the era colour is a comparison chain on
  `published`.
- **Era chips** — filter on the same five buckets the spine wall colours by.
  `main.js` tags every row with `data-era` at startup; the chips combine with
  the search rather than replacing it, and clicking the active chip clears it.
- **Sticky bar on mobile** — the controls stay pinned, but the jump rail is
  hidden and the era chips scroll sideways rather than wrapping onto three
  lines, so the bar stays near the height of the search field plus one row.
- **Watch heatmap** — a year × month grid on the Stats page. Books carry only
  a year, so movies are the one part of the log fine-grained enough to show a
  rhythm. Shading is bucketed into six levels in Liquid, which has no float
  division. The current year is zero-filled only through the current month
  (`build_stats.py` checks against `datetime.date.today()`) — a month that
  has not happened yet gets `count: null` and a distinct hatched `.heat--future`
  cell, rather than being shaded identically to a month with genuinely
  nothing watched. Without that, the row for the year in progress would trail
  off into a stretch of flat "zero" cells indistinguishable from an actual
  quiet spell.
- **Generated images** — `build_images.py` writes PNG by hand (zlib + struct,
  no image library) because both images are axis-aligned rectangles and no
  text is drawn. Link previews render `og:title` beside the image, and a
  favicon has no room for words.

## Adding dev notes

`docs/dev/vim-tips.markdown` is edited directly — no build step. For a new
topic, add a page under `docs/dev/` with `permalink: /dev/<name>/` and a card
for it in `docs/dev.markdown`.

## Cover art

Covers load lazily as rows scroll into view, at most 4 requests at a time, and
results are cached in `localStorage` (including misses, so a failed lookup is
not retried every visit).

- **Books** — by ISBN straight from Open Library when known (416 of 563), which
  needs no search request and cannot mismatch. Books without an ISBN fall back
  to a title/author search.
- **Movies** — TMDB. The API key in `assets/js/main.js` is a free personal key
  and is necessarily public in a static site's JavaScript; regenerate it in
  your TMDB account settings if it is ever abused.

If covers look wrong after changing the lookup logic, bump `COVER_CACHE_PREFIX`
in `main.js` so stale cached results are discarded.

## Running locally

```sh
cd docs
bundle install
bundle exec jekyll serve
```

Then <http://127.0.0.1:4000>. In a Bloomberg Space, Ruby is not on `PATH` by
default:

```sh
export PATH="/opt/bb/bin/ruby3.1:$PATH"
```

Note the local `Gemfile` pins `github-pages`, which tracks the Jekyll version
GitHub Pages actually builds with — worth using rather than a newer Jekyll, so
local output matches production.

## Link previews

`jekyll-seo-tag` generates the `<title>`, `description` and Open Graph tags
that Slack, iMessage and social sites read. Every page carries its own
`description:` in its front matter; without one it inherits the site-wide
description, which makes every link preview read identically.

The `og:image` is `assets/social-card.png`, drawn from the shelf by
`build_images.py` — one spine per book, width by page count, colour by era —
so the card is the actual collection rather than a logo, and it changes as the
shelf grows. Note that `jekyll-seo-tag` reads `page.image` and does **not**
fall back to `site.image`, so it is set through Jekyll `defaults` in
`_config.yml`, not as a plain site key.

## CI

`.github/workflows/build.yml` runs two checks on every push and pull request:

- **data** — re-runs `scripts/build.py` and fails if `docs/_data` changes,
  which catches editing a markdown log without regenerating the JSON.
- **site** — a full `jekyll build`, which catches Liquid and front-matter
  errors.

Both are advisory. GitHub Pages builds and deploys independently of this
workflow, so a red run does not block a deploy — it just tells you the
published site is wrong. Both failure modes are otherwise silent: stale data
looks fine until you notice a missing book, and a Liquid error leaves the
previous version of the page published.
