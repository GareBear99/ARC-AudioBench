"""Alias test (scripts/alias_test.py).

The band-limited sawtooth must PASS (no alias peaks above the -80 dBFS
floor) and the naive sawtooth must FAIL (the negative control -- if the
naive sawtooth ever passes, the test is not detecting aliasing).
Headline numbers are pinned to the committed results in results/alias/.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from helpers import ROOT, TONES, BenchTestCase, approx, load_committed

import alias_test


class TestAlias(unittest.TestCase):
    def test_bandlimited_passes(self):
        wav = TONES / "sawtooth_bandlimited_997hz.wav"
        r = alias_test.analyze_alias(wav, 997.0)
        self.assertTrue(r["pass"])
        self.assertEqual(r["alias_peak_count"], 0)
        self.assertIsNone(r["worst_alias_dbfs"])
        self.assertEqual(r["schema_version"], "arc-audiobench-alias-v1")
        self.assertEqual(r["fundamental_hz"], 997.0)

    def test_naive_fails_negative_control(self):
        wav = TONES / "sawtooth_naive_997hz.wav"
        r = alias_test.analyze_alias(wav, 997.0)
        self.assertFalse(r["pass"])
        self.assertEqual(r["alias_peak_count"], 2135)
        self.assertTrue(approx(r["worst_alias_dbfs"], -38.252))
        self.assertTrue(approx(r["worst_alias_hz"], 22078.125))
        self.assertTrue(approx(r["alias_to_signal_ratio_db"], -15.849))

    def test_regression_matches_committed(self):
        for name, committed in (
            ("sawtooth_bandlimited_997hz.wav",
             "alias/sawtooth_bandlimited_997hz.alias.json"),
            ("sawtooth_naive_997hz.wav",
             "alias/sawtooth_naive_997hz.alias.json"),
        ):
            r = alias_test.analyze_alias(TONES / name, 997.0)
            c = load_committed(committed)
            self.assertEqual(r["pass"], c["pass"], name)
            self.assertEqual(r["alias_peak_count"], c["alias_peak_count"], name)
            self.assertTrue(approx(r["worst_alias_dbfs"], c["worst_alias_dbfs"]), name)
            self.assertTrue(approx(r["alias_to_signal_ratio_db"],
                                   c["alias_to_signal_ratio_db"]), name)

    def test_laxer_threshold_passes_naive(self):
        # The naive sawtooth fails the default thresholds (worst alias
        # -38.252 dBFS vs -60, ASR -15.849 dB vs -40). With thresholds
        # laxer than both measured values it must pass, proving the
        # thresholds are actually applied.
        wav = TONES / "sawtooth_naive_997hz.wav"
        r = alias_test.analyze_alias(wav, 997.0, worst_alias_db=-30.0,
                                     asr_db=-10.0)
        self.assertTrue(r["pass"])

    def test_dbfs_helper(self):
        # Hann window: a full-scale sine gives |X| = N/4 at its peak
        # bin (coherent gain 0.5, single-sided spectrum), so N/4 reads
        # 0 dBFS and N/8 reads -6.02 dBFS.
        self.assertAlmostEqual(alias_test._dbfs_from_fft_mag(4096.0, 16384), 0.0, places=6)
        self.assertAlmostEqual(alias_test._dbfs_from_fft_mag(2048.0, 16384), -6.0206, places=3)


if __name__ == "__main__":
    unittest.main()
