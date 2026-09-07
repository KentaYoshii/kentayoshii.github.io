#!/usr/bin/env python3
"""Regenerate every docs/_data file, in dependency order.

    python3 scripts/build.py

Equivalent to running merge_books.py, build_movies.py, build_covers.py,
build_stats.py, build_images.py and build_travel.py in sequence — each later
step reads the output of an earlier one, so the order matters. build_travel.py
has no dependency on the others; it just runs alongside them for one entry
point.

Every step here is offline and deterministic, which is what lets CI re-run
this and byte-compare the result. build_covers.py is the one step with a
network mode, and it is not reached from here: filling its cache is a manual
`python3 scripts/build_covers.py --fetch`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_covers  # noqa: E402
import build_images  # noqa: E402
import build_movies  # noqa: E402
import build_stats  # noqa: E402
import build_trails  # noqa: E402
import build_travel  # noqa: E402
import merge_books  # noqa: E402

# build_covers annotates books.json and movies.json, so it runs after both are
# written and before build_stats, whose cover mosaic reads the annotations.
# build_images reads books.json for ISBNs, so it too runs after merge_books.
# build_travel and build_trails are independent of all of the above and of
# each other; they run here so one command regenerates everything.
for step in (merge_books, build_movies, build_covers, build_stats,
             build_images, build_travel, build_trails):
    step.main()
