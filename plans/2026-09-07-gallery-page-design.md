# Gallery page design

Date: 2026-09-07

Note: the skill convention for this doc is `docs/plans/...`, but `docs/` in
this repo *is* the Jekyll site source — anything dropped there gets copied
into the published site. This doc lives at the repo root instead so it isn't
published.

## Goal

A `/gallery/` page for personal photos, in the style of the site's existing
collection pages (Books, Movies, Adventure) but for images rather than
records about books/films/trails.

## Storage

- Image files: committed under `docs/assets/gallery/`. No resizing/thumbnail
  pipeline, no size constraint (enforced or documented) — out of scope per
  explicit decision.
- Metadata: a single hand-maintained `docs/_data/gallery.yml`, newest first:

  ```yaml
  - image: /assets/gallery/2026-06-yosemite-valley.jpg
    caption: Tunnel View at sunrise
    date: 2026-06-14
    location: Yosemite National Park, CA
    tags: [landscape, national-park]
  ```

- No `_logs/gallery.md` + Python build script, unlike books/movies/trails.
  Those exist because their sources need external API resolution (covers,
  posters) or free-text date-heading parsing that Liquid can't do. A gallery
  entry has no external lookup and its fields are already structured, so
  hand-editing YAML directly is simpler than round-tripping through a
  generator. Adding a photo = drop the file + add one YAML block. No changes
  to `scripts/build.py` or CI's data-drift check are needed.

## Page (`docs/gallery.markdown`)

- Front matter: `layout: page`, `permalink: /gallery/`, a `description:`.
- Added to `header_pages` in `_config.yml`, right after `adventure.markdown`.
- Tag chips row above the grid: built in Liquid from the deduplicated set of
  `tags` across `site.data.gallery`, same interaction pattern as the era
  chips on Stats (click to filter, click active chip to clear).
- Grid: one `<div class="gallery-grid">` of thumbnail tiles. Each tile is an
  `<img>` with `loading="lazy"`, `alt` from `caption`, and
  `data-caption`/`data-date`/`data-location`/`data-tags` attributes for the
  lightbox and filter JS to read. `object-fit: cover` on a fixed-aspect box
  keeps the grid even without per-image thumbnail generation.

## Lightbox (`assets/js/main.js`)

New `initGalleryLightbox()`, called only on the gallery page (guarded by
checking the grid exists, same pattern as other page-specific `init*`
functions):

- Click a tile → full-screen overlay: the full-res image (same file — no
  separate thumbnail vs. full-size asset), caption/date/location text below
  it, prev/next arrows, and a close button.
- Close via `Esc`, backdrop click, or the close button.
- `ArrowLeft`/`ArrowRight` move between photos while the lightbox is open,
  wrapping at the ends.
- Tag filtering: clicking a chip toggles `hidden` on tiles whose
  `data-tags` doesn't include the selected tag, and rebuilds the array the
  lightbox uses for prev/next so it only cycles through currently-visible
  photos.

## Styling (`assets/main.scss`)

New rules alongside the existing `.park-grid`/`.collection-items` block:
`.gallery-grid` (responsive `grid-template-columns: repeat(auto-fill, ...)`),
`.gallery-tile`, `.gallery-lightbox` (fixed overlay, centered image, arrow
buttons), reusing existing chip styles (`.tag`/`.chip`-equivalent, whatever
the era-chip class is actually named) for the tag row rather than introducing
a parallel set of chip styles.

## Edge cases

- Empty `gallery.yml` → page renders the tag row as empty and the grid as
  empty; no "nothing here yet" message was requested, so none is added
  (matches YAGNI — can add later if it looks bare).
- A photo with no `tags` → simply contributes no chips; still renders in the
  grid and in the "all photos" (unfiltered) view.
- Lightbox JS failing/disabled → thumbnails are plain `<img>` tags with no
  `href` wrapper needed for basic viewing at grid size; there's no
  `<a href="full.jpg">` fallback since a no-JS full-res view was not
  requested and the grid image *is* the full image (no separate thumbnail
  file to fall back from).

## Testing

- No Python code is added (no build script), so no new pytest coverage.
- CI's existing `site` job (`jekyll build`) exercises the new Liquid/front
  matter for syntax errors.
- Manually verify in a local `bundle exec jekyll serve`: grid renders test
  entries, chip filter narrows the grid, lightbox opens/closes/navigates,
  dark mode and mobile layout look right (same manual bar as the rest of the
  site — no existing UI test harness to hook into).

## Out of scope (explicitly decided against)

- Automated image size enforcement (CI check or otherwise).
- Documented size/compression guidance in the README.
- Masonry/variable-height layout.
- Per-photo thumbnail generation distinct from the full-res file.
