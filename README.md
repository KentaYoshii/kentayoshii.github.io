# Kenta's Log

A personal log of books read, movies/shows watched, and dev notes.
Live at <https://kentayoshii.github.io>.

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
  _logs/books.md          hand-written reading log (source of truth)
  _logs/movies.md         hand-written watch log (source of truth)
  _posts/                 blog posts only (`categories: posts`)
  books.markdown          renders _data/books.json
  movies.markdown         renders _data/movies.json
  stats.markdown          renders _data/stats.json
  posts.markdown          lists posts filed under `categories: posts`
  404.html                served by GitHub Pages for any unmatched path
  dev/vim-tips.markdown   dev notes, edited directly
  assets/js/main.js       search, grouping, cover art, dark mode
  assets/main.scss        theme
scripts/
  build.py                runs all three, in order — the usual entry point
  merge_books.py          builds _data/books.json
  build_movies.py         builds _data/movies.json
  build_stats.py          builds _data/stats.json (reads the other two)
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
its ISBN and therefore its cover. If a book is missing a cover, check its
spelling first — the script prints a matched/unmatched count each run.

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
- **Landing page mosaic** — 36 ISBNs chosen at build time by striding through
  the title-sorted shelf (`MOSAIC_COUNT` in `build_stats.py`), so it is not 36
  books beginning with "A". Decorative and `aria-hidden`.
- **Spine wall** — rendered in Liquid from `_data/books.json`, no extra data:
  width is `pages / 40` and the era colour is a comparison chain on
  `published`.

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

There is no `og:image`, so previews render as small text-only cards. To
upgrade them to large image cards, add a raster image (PNG or JPG — SVG is not
reliably supported) and point `_config.yml` at it:

```yaml
image: /assets/social-card.png
```

Recommended size is 1200×630. Do not reference a file that does not exist —
a broken `og:image` previews worse than none at all.

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
