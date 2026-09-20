# Gallery rework

Date: 2026-09-19

Supersedes parts of `2026-09-07-gallery-page-design.md`. Same note as that
doc: this lives at the repo root rather than under `docs/`, because `docs/`
is the Jekyll source and anything dropped there gets published.

## Why

Three complaints about `/gallery/`: the wording was flat, the alignment looked
off, and loading felt slow. Each traced to a specific decision in the original
design rather than to a bug.

## What was wrong

**Loading.** The page served the committed originals straight into the grid —
153 MB across 36 photos, several over 6 MB, every one scaled down by the
browser into a box a few hundred pixels wide. `loading="lazy"` deferred the
cost without removing it.

**Alignment.** Two independent causes:

- The `<img>` tags declared no `width`/`height`, so each tile had no height
  until its photo arrived and the layout reflowed continuously as they landed.
- `.gallery-grid` used `columns: 4`. CSS multi-column fills *down* column one
  before column two, so a list in date order read top-to-bottom per column
  rather than left-to-right.

The masonry layout was chosen so photos could keep their own aspect ratios.
Measured across the actual set, 35 of 36 are 4:3 and one is portrait — so it
was solving a problem this collection does not have, while causing two it did.

**Nothing distinctive.** `description: Photos I've taken.` over a bare count.

Two data faults turned up while investigating: `grand_teton_1.jpeg` was on
disk but missing from `gallery.yml`, and the `portrait`/`panorama`/`square`
tags did not match the images they described (`grand_canyon` was tagged
`panorama` at 4:3). Nearly every entry read `location: Test bench`.

## Decisions revisited from 2026-09-07

That document explicitly ruled out, as out of scope:

- per-photo thumbnail generation distinct from the full-resolution file;
- masonry / variable-height layout (it was later built anyway);
- documented size or compression guidance.

The first is the direct cause of the slow loading and is now built. The second
was built and is now removed, for the reasons above. The third is replaced by
something better than guidance: the generator makes the page's cost
independent of how large the originals are, so there is no rule to follow.

## What was built

**Derivatives.** `scripts/build_gallery_thumbs.py` writes an 800px copy for
the grid and a 2000px copy for the lightbox. The grid went from 153.5 MB to
3.5 MB, measured. Originals stay committed as the rebuild source and are no
longer linked from anywhere.

It needs Pillow, so it is deliberately not in `build.py`: CI runs that with
nothing installed and the rest of `scripts/` is standard-library only. It is a
manual pass whose output is committed — the arrangement `build_covers.py
--fetch` already uses.

**Grouping.** The page is now one section per park, joined to
`_data/travel.json` on a new `park` field for each park's state and visit
year, and linked back to `/adventure/`. The join is on an explicit field
rather than on the caption because the spellings diverge on six of fourteen
parks (`Whitesands` against `White Sands`, and so on).

**Colour.** Each section is tinted with a colour measured from its own
photographs. The first attempt averaged pixels and was abandoned: a mean
landscape converges on the same grey-blue everywhere, and thirteen of the
fourteen parks came out within a few percent of each other. Grand Teton,
whose average was near-neutral, had its essentially meaningless hue amplified
into a confident green.

What works instead: quantise, drop the top 40% of the frame, and weight
clusters by saturation. The sky crop matters because sky is the most saturated
region in most of these photos and looks the same above every park — the
ground is what tells them apart. Hues now run from 28° to 230°.

Combining a park's photos averages hue as an angle rather than in RGB, so a
park with an orange canyon and a blue lake does not come out grey.

**Placeholders.** A 16px-wide copy of each photo is inlined as a data URI and
the real image fades in over it. All 36 come to 16.8 KB, so the grid is never
empty boxes.

**Map.** `scripts/build_gallery_map.py --fetch` pulls us-atlas TopoJSON (US
Census cartographic boundaries, public domain) and projects it through Albers
USA, with Alaska and Hawaiʻi in the usual insets. Hawaiʻi is not optional
here: two of the parks are there and would otherwise project into the Pacific.

The geometry is unprojected, which is why it was chosen. The outlines and the
park markers go through one projection implemented once, so they cannot
disagree — and `tests/integration/test_gallery_map_data.py` checks that every
marker lands inside its own state polygon, which is the assertion that would
catch a wrong constant. A pre-projected outline would have meant reproducing
whatever projection it used and hoping.

Markers are parks rather than states because five states hold two parks each.
They are ordinary anchors to the section ids, so the map works without
JavaScript; `main.js` only upgrades the jump to a smooth scroll and clears an
active filter first.

## Data left unset on purpose

The placeholder `caption`, `date` and `tags` values were removed and not
replaced. Real values exist for park, state and visit year and those are now
in place; nothing is known about the dates the photos were taken, what they
show, or how to tag them, so the keys are documented as optional and left
empty rather than filled with plausible-looking inventions. Antelope Canyon
keeps its caption, which is genuine.

## Not done

- **Captions.** Worth adding when there is something real to say; the template
  already prefers `caption` over the park name for both alt text and the
  hover overlay.
- **A `webp`/`avif` variant.** The JPEG thumbnails are around 100 KB and the
  grid is no longer the bottleneck, so this would be optimisation without a
  measured problem.
- **`stats.json` drift.** `build.py` regenerates it with different TMDB poster
  URLs than are committed, so CI's data-drift job fails. This predates the
  rework — confirmed on a clean worktree of the base commit — and was left
  alone to keep the change focused.
