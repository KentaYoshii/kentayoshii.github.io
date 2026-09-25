# 2026-09-25 (5) — Add more Japanese films to the Movies page

## Tasks

- Add a second batch of Japanese films, filed in the ## Undated backlog like
  the prior Japanese batch (no watch year given).

## Changes

- `docs/_logs/movies.md` — added 10 entries to `## Undated`:
  - Thermae Romae, Thermae Romae II (from "Thermae Romae (1 and 2)")
  - Wolf Children
  - Rurouni Kenshin (2012), Rurouni Kenshin: Kyoto Inferno, Rurouni Kenshin:
    The Legend Ends, Rurouni Kenshin: The Final, Rurouni Kenshin: The
    Beginning (all 5 live-action films, listed individually per the user;
    the first tagged (2012) to mark it as the series opener)
  - The Eternal Zero
  - Bakuman
- `docs/_data/movies.json`, `docs/_data/stats.json` — regenerated. Movie count
  415 -> 425.

## Verification

- `python3 scripts/build.py` — clean run.
- `python3 -m pytest -q` — 387 passed, 2 skipped.

## TODOs

- New titles have no poster yet; run the `fetch` workflow (target `covers`).
