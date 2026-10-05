# 2026-10-05 — Add the Fast & Furious films to the Movies page

## Tasks

- Add all Fast & Furious films. No watch date given; filed under
  `## 2026` / `### October` (current month).

## Changes

- `docs/_logs/movies.md` — new `### October` section under `## 2026` with 11
  entries in release order: The Fast and the Furious (2001), 2 Fast 2 Furious,
  The Fast and the Furious: Tokyo Drift, Fast & Furious (2009), Fast Five,
  Fast & Furious 6, Furious 7, The Fate of the Furious, Fast & Furious
  Presents: Hobbs & Shaw, F9, Fast X. Year tags on the 2001 and 2009 titles
  separate them from same-named films on TMDB.
- `docs/_data/movies.json`, `docs/_data/stats.json` — regenerated. Movie count
  425 -> 436.

## Verification

- `/opt/bb/bin/python3.13 scripts/build.py` — clean run (`python3` is not on
  PATH in this Space).
- pytest not run: not installed for the available interpreter.

## TODOs

- New titles have no poster yet; run the `fetch` workflow (target `covers`).
- Fast X: Part 2 (2027) is unreleased; add when watched.
