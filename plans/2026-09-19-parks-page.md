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
3.5 MB, measured.

The originals then moved to `photo-originals/` at the repo root. Unlinking
them from the page was not enough: `docs/` is the Jekyll source, so everything
under it is copied into the built site regardless of what links to it, and the
originals were still being published at guessable URLs and shipped in every
deploy. Moving them outside `docs/` was the fix — a Jekyll `exclude` would
not work, because the derivatives live inside `assets/gallery/` and would have
gone with it. They remain committed, because the generator reads them.

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

## Dates, and what the EXIF turned up

The placeholder `caption`, `date` and `tags` values were first removed rather
than replaced, on the grounds that nothing real was known to put there. That
was right about captions and wrong about dates: every photo carries an EXIF
`DateTimeOriginal`, so the dates were recoverable and are now recorded. The
lightbox shows the photo's own date, falling back to the park's visit year.

34 of the photos also carry GPS, which turned the park field into something
checkable. Two things came out of checking it:

- `yosemite_1.jpeg` was 7,274 miles from Yosemite — 44.76°S, 167.96°E, which
  is Fiordland in New Zealand — and dated more than a year before the genuine
  Yosemite photos. It had been mislabelled since before this rework. The photo
  has been removed from the gallery; it is in git history if it is ever
  wanted. Yosemite's accent colour changed once it stopped being averaged with
  a photograph from the wrong hemisphere.
- `hawaiian_volcanoes_1.jpeg` is dated April 2022, but `_logs/travel.md`
  listed Hawaiʻi Volcanoes under 2026. The Haleakalā photos confirm a 2026
  Hawaii trip, so the log had one park under the wrong year; it now sits under
  2022, which is what the photograph supports.

Captions and tags were then written by looking at each photograph. Where a
landmark is not identifiable with certainty the caption describes what is
visible rather than naming it — "Looking out through the pour-off" rather
than a specific named feature. Tags are shown in the lightbox; the filter
chips remain park-based, since parks are what the page is organised by.

## Not done

- **A `webp`/`avif` variant.** The JPEG thumbnails are around 100 KB and the
  grid is no longer the bottleneck, so this would be optimisation without a
  measured problem.
- **Tag filtering.** Tags are recorded and displayed but not filterable. The
  chip row filters by park, and a second axis of filtering is more machinery
  than 35 photos justify.

---

# Folding the gallery into a parks page

Date: 2026-09-20

## Why

Two pages were describing the same sixty-three parks. `/adventure/` held the
checklist next to an unrelated trail log; `/gallery/` held photographs grouped
by park, with a park map. Thirty-four of the thirty-five photographs are of
national parks, and `/gallery/` was reachable only from the nav's "More"
dropdown — the home page did not link to it at all.

So the split was along the wrong axis. Not Adventure-and-Gallery, but
parks-and-trails.

## What it is now

```
/adventure/          hub, a card per child (same shape as /dev/)
/adventure/parks/    map → checklist → photographs
/adventure/trails/   the trail log
/gallery/            redirect stub
```

The hub's cards carry live counts rather than static blurbs, so it says
something rather than only pointing. Nav drops from seven entries to six,
which let `adventure.markdown` move out of the "More" dropdown and back inline.

The checklist stays. A map cannot label sixty-three dots, so it is not a
substitute for the part you read names and years off; it sits above it.

## The map, extended

`build_gallery_map.py` became `build_parks_map.py`, and its coordinate table
went from the fourteen photographed parks to all sixty-three. Routing to a
sub-projection is now decided from the coordinate rather than from a state
code typed alongside it — one fewer field to get wrong, and a park nowhere
near the United States reports that instead of landing in Kansas.

Markers have three states: hollow for unvisited, filled for visited, filled
with the park's own measured colour where there are photographs. Each is an
anchor — to the photo section where one exists, to the checklist tile
otherwise — so every dot leads somewhere and the map works without JavaScript.

Two parks have no marker. Albers USA covers the fifty states and nothing else,
so American Samoa and Virgin Islands are listed in `UNPLOTTABLE` and the
caption says so, rather than showing 61 dots beside the number 63.

Forty-nine coordinates were entered by hand. That is safe only because the
integration test projects each one and checks it lands inside the state
`national_parks.py` lists it under. Four parks legitimately fall outside their
state's simplified outline — Dry Tortugas 0.1px, Biscayne 0.5px, Gateway Arch
0.6px, Isle Royale 1.1px, all islands or riverbanks — so the check allows 3px.
A mistyped coordinate misses by hundreds.

## What this costs

`docs/adventure/parks.markdown` reads `checklists.us_national_parks` by name
instead of looping over every category the way the old page did. A new
checklist no longer appears on a page automatically; it needs its own page and
a card on the hub. That is a real loss of generality, accepted because the
parks page pairs the checklist with park coordinates and with photographs
joined on park name — neither of which means anything for a list of countries.
