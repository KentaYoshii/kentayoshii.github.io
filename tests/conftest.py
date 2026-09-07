"""Shared test setup.

The build scripts are standalone files run as ``python3 scripts/<name>.py``
rather than an installed package, so there is no import path to configure in
packaging metadata. Put ``scripts/`` on ``sys.path`` here instead, which keeps
the scripts importable from tests without turning the repo into a package.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
