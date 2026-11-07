"""Therum integration: run the Bench's measurements on the real
Therum renders (sibling repo, read-only). These are the numbers the
Therum paper's section 7 acceptance test is judged by:

- Step 2 (aliasing): mipped wavetable worst alias -45.80 dBFS at
  22078 Hz, ASR -33.23 dB; naive -32.24 dBFS, ASR -16.01 dB.
- Step 2 (NMR): the 22 kHz alias is well masked (NMR -69.80 dB);
  the failure is the low-frequency folded harmonics -- worst NMR
  +23.31 dB (mipped) / +42.04 dB (naive) at 143.6 / 287.1 Hz.

Skipped (not failed) when the Therum repo or its renders are absent.
"""
from __future__ import annotations

import unittest

from helpers import THERUM_TESTS, approx

import alias_test
import nmr_test

NAIVE = THERUM_TESTS / "wavetable_997hz_naive.wav"
MIPPED = THERUM_TESTS / "wavetable_997hz.wav"


@unittest.skipUnless(NAIVE.exists() and MIPPED.exists(),
                     "Therum wavetable renders absent")
class TestTherumIntegration(unittest.TestCase):
    def test_mipped_alias_matches_paper(self):
        r = alias_test.analyze_alias(MIPPED, 997.0)
        self.assertFalse(r["pass"])  # real render: still aliases, just less
        self.assertTrue(approx(r["worst_alias_dbfs"], -45.804, tol=0.05))
        self.assertTrue(approx(r["worst_alias_hz"], 22078.125))
        self.assertTrue(approx(r["alias_to_signal_ratio_db"], -33.226, tol=0.05))

    def test_naive_alias_matches_paper(self):
        r = alias_test.analyze_alias(NAIVE, 997.0)
        self.assertFalse(r["pass"])
        self.assertTrue(approx(r["worst_alias_dbfs"], -32.235, tol=0.05))
        self.assertTrue(approx(r["alias_to_signal_ratio_db"], -16.008, tol=0.05))

    def test_mipped_beats_naive_on_both_measures(self):
        mipped_alias = alias_test.analyze_alias(MIPPED, 997.0)
        naive_alias = alias_test.analyze_alias(NAIVE, 997.0)
        self.assertLess(mipped_alias["alias_peak_count"],
                        naive_alias["alias_peak_count"])
        self.assertLess(mipped_alias["alias_to_signal_ratio_db"],
                        naive_alias["alias_to_signal_ratio_db"])
        mipped_nmr = nmr_test.analyze_nmr(MIPPED, 997.0)
        naive_nmr = nmr_test.analyze_nmr(NAIVE, 997.0)
        self.assertLess(mipped_nmr["worst_nmr_db"], naive_nmr["worst_nmr_db"])

    def test_nmr_matches_committed(self):
        from helpers import load_committed
        mipped = nmr_test.analyze_nmr(MIPPED, 997.0)
        naive = nmr_test.analyze_nmr(NAIVE, 997.0)
        cm = load_committed("nmr/therum_mipped_997hz.nmr.json")
        cn = load_committed("nmr/therum_naive_997hz.nmr.json")
        self.assertFalse(mipped["pass"])
        self.assertFalse(naive["pass"])
        self.assertTrue(approx(mipped["worst_nmr_db"], cm["worst_nmr_db"]))
        self.assertTrue(approx(naive["worst_nmr_db"], cn["worst_nmr_db"]))
        self.assertTrue(approx(mipped["worst_nmr_db"], 23.308))
        self.assertTrue(approx(naive["worst_nmr_db"], 42.043))


if __name__ == "__main__":
    unittest.main()
