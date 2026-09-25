# 2026-09-25 (4) — Add Japanese films to the Movies page

## Tasks

- Add a batch of Japanese films from a user-pasted list mixing single films,
  enumerated pairs, and large movie series.

## Key decisions (confirmed with user)

- Large series (Detective Conan ~28 films, One Piece ~15, Naruto ~11) added
  as a single umbrella entry each rather than every film, to avoid ~54
  separate entries: "Detective Conan (movie series)", "One Piece (movies)",
  "Naruto (movies)".
- Death Note -> first two live-action films only.
- Gantz -> both live-action films (not Gantz:O).
- No watch year given, so all filed under the ## Undated backlog.

## Changes

- `docs/_logs/movies.md` — added 11 entries to `## Undated`:
  - Death Note (2006), Death Note: The Last Name
  - Detective Conan (movie series)
  - Gantz (2011), Gantz: Perfect Answer
  - Gokusen: The Movie
  - Kaiji, Kaiji 2
  - Naruto (movies)
  - One Piece (movies)
  - Summer Wars
  - Year tags on "Death Note (2006)" and "Gantz (2011)" disambiguate from the
    2017 Netflix Death Note and the Gantz:O anime respectively.
- `docs/_data/movies.json`, `docs/_data/stats.json` — regenerated. Movie count
  404 -> 415.

## Verification

- `python3 scripts/build.py` — clean run.
- `python3 -m pytest -q` — 387 passed, 2 skipped.

## TODOs

- New titles have no poster yet; run the `fetch` workflow (target `covers`).
  Poster lookup for the umbrella-series entries and Japanese titles may not
  resolve cleanly against TMDB — worth checking after the next fetch.
