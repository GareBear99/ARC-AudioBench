"""NMR test (scripts/nmr_test.py) -- Therum paper section 7 headline test.

Aliases are judged against the auditory masking curve, not a bare dB
number. The band-limited sawtooth must PASS (worst NMR None -- no alias
above the floor) and the naive sawtooth must FAIL with worst NMR +36.046
dB. The psychoacoustic helpers (Bark, spreading, ATH) are pinned to
sanity values so a broken formula cannot silently pass.
"""
from __future__ import annotations

import unittest

from helpers import TONES, approx, load_committed

import nmr_test


class TestNmr(unittest.TestCase):
    def test_bandlimited_passes(self):
        r = nmr_test.analyze_nmr(TONES / "sawtooth_bandlimited_997hz.wav", 997.0)
        self.assertTrue(r["pass"])
        self.assertEqual(r["alias_peak_count"], 0)
        self.assertIsNone(r["worst_nmr_db"])
        self.assertEqual(r["schema_version"], "arc-audiobench-nmr-v1")

    def test_naive_fails_negative_control(self):
        r = nmr_test.analyze_nmr(TONES / "sawtooth_naive_997hz.wav", 997.0)
        self.assertFalse(r["pass"])
        self.assertTrue(approx(r["worst_nmr_db"], 36.046))
        self.assertTrue(approx(r["worst_nmr_hz"], 287.109))
        self.assertEqual(r["alias_peak_count"], 2135)

    def test_regression_matches_committed(self):
        for name, committed in (
            ("sawtooth_bandlimited_997hz.wav", "nmr/sawtooth_bandlimited_997hz.nmr.json"),
            ("sawtooth_naive_997hz.wav", "nmr/sawtooth_naive_997hz.nmr.json"),
        ):
            r = nmr_test.analyze_nmr(TONES / name, 997.0)
            c = load_committed(committed)
            self.assertEqual(r["pass"], c["pass"], name)
            self.assertTrue(approx(r["worst_nmr_db"], c["worst_nmr_db"]), name)
            self.assertEqual(r["alias_peak_count"], c["alias_peak_count"], name)

    def test_bark_scale_sanity(self):
        # Zwicker 1961: 1000 Hz is ~8.5 Bark, 100 Hz is ~1 Bark.
        self.assertAlmostEqual(nmr_test.bark(1000.0), 8.5, delta=0.2)
        self.assertAlmostEqual(nmr_test.bark(100.0), 1.0, delta=0.3)
        self.assertLess(nmr_test.bark(100.0), nmr_test.bark(1000.0))
        self.assertLess(nmr_test.bark(1000.0), nmr_test.bark(10000.0))

    def test_spreading_function_sanity(self):
        # Schroeder, Atal & Hall 1979 (MPEG-1 Model 1): the spreading
        # function is ~0 dB at zero Bark distance and falls off steeply
        # with distance on both sides (asymmetric: the low side falls
        # faster).
        self.assertAlmostEqual(nmr_test.spreading_db(0.0), 0.0, delta=0.01)
        self.assertLess(nmr_test.spreading_db(3.0), nmr_test.spreading_db(0.0))
        self.assertLess(nmr_test.spreading_db(-3.0), nmr_test.spreading_db(0.0))
        self.assertLess(nmr_test.spreading_db(10.0), -80.0)

    def test_ath_minimum_near_4khz(self):
        # Terhardt 1979: the absolute threshold of hearing is lowest
        # around 3-4 kHz and much higher at 100 Hz and 16 kHz.
        ath_100 = nmr_test.ath_db_spl(100.0)
        ath_4000 = nmr_test.ath_db_spl(4000.0)
        ath_16000 = nmr_test.ath_db_spl(16000.0)
        self.assertLess(ath_4000, ath_100)
        self.assertLess(ath_4000, ath_16000)
        self.assertLess(ath_4000, 0.0)  # ~-5 dB SPL at 4 kHz


if __name__ == "__main__":
    unittest.main()
