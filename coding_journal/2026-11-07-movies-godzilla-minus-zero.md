# 2026-11-07 — Add Godzilla Minus Zero to the Movies page

## Tasks

- Add Godzilla Minus One and its sequel. Minus One was already logged
  (`## 2024` / `### June`), so only the sequel was added. No watch date
  given; filed under `## 2026` / `### November` (current month, release week).

## Changes

- `docs/_logs/movies.md` — new `### November` section under `## 2026` with
  Godzilla Minus Zero.
- `docs/_data/movies.json`, `docs/_data/stats.json` — regenerated. Movie count
  439 -> 440.

## Verification

- `python3 scripts/build.py` — clean run.

## TODOs

- New title has no poster yet; run the `fetch` workflow (target `covers`).
