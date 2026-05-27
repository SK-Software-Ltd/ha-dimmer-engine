"""Conftest for compatibility smoke tests.

Kept separate from tests/conftest.py because smoke tests must not require
the HA event loop / fixtures — they exercise import + instantiation only.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
