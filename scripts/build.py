#!/usr/bin/env python3
"""Regenerate every docs/_data file, in dependency order.

    python3 scripts/build.py

Equivalent to running merge_books.py, build_movies.py, build_stats.py,
build_images.py and build_travel.py in sequence — each later step reads the
output of an earlier one, so the order matters. build_travel.py has no
dependency on the others; it just runs alongside them for one entry point.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_images  # noqa: E402
import build_movies  # noqa: E402
import build_stats  # noqa: E402
import build_travel  # noqa: E402
import merge_books  # noqa: E402

# build_images reads books.json, so it runs after merge_books.
for step in (merge_books, build_movies, build_stats, build_images, build_travel):
    step.main()
