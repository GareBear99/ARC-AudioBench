"""Shared helpers for the ARC-AudioBench test suite.

The measurement scripts live in ``scripts/`` and import each other by
top-level module name (``from analyze_wav import ...``), so the tests put
``scripts/`` on ``sys.path`` before importing them. All tests run against
the committed test tones in ``data/test_tones/`` plus tones generated into
a temporary directory -- no network, no Mac, no plugin host required.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TONES = ROOT / "data" / "test_tones"
RESULTS = ROOT / "results"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# The Therum renders live in the sibling Therum repo (read-only here).
THERUM_TESTS = Path.home() / "workspace" / "Therum_JUCE-Plugin" / "Therum-Core-Engine" / "Tests"


def load_committed(relpath: str) -> dict:
    """Load a committed result JSON from results/."""
    return json.loads((RESULTS / relpath).read_text(encoding="utf-8"))


def approx(a, b, tol=0.01):
    """True when two numbers agree within tol (None matches only None)."""
    if a is None or b is None:
        return a is b
    return abs(a - b) <= tol


class BenchTestCase(unittest.TestCase):
    """Base case: the committed test tones must exist."""

    def assertCommittedTone(self, name: str) -> Path:
        p = TONES / name
        self.assertTrue(p.exists(), f"committed test tone missing: {p}")
        return p
