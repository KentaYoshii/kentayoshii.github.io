#!/usr/bin/env python3
"""Regenerate every docs/_data file, in dependency order.

    python3 scripts/build.py

Equivalent to running merge_books.py, build_movies.py and build_stats.py in
sequence — stats reads the output of the other two, so the order matters.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_movies  # noqa: E402
import build_stats  # noqa: E402
import merge_books  # noqa: E402

for step in (merge_books, build_movies, build_stats):
    step.main()
