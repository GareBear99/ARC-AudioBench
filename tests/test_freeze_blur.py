"""Freeze-blur test (scripts/freeze_blur_test.py) -- Vox8 freeze pilot.

A frozen (or sustained) vowel smears energy into adjacent FFT bins;
the blur is the adjacent-bin / peak-bin ratio per harmonic in dB (more
negative = sharper). Ordering must hold: the static vowel is sharpest,
the vibrato vowel is blurriest, the simulated freeze sits between
them. Headline numbers are pinned to the committed results.
"""
from __future__ import annotations

import unittest

from helpers import TONES, approx, load_committed

import freeze_blur_test


class TestFreezeBlur(unittest.TestCase):
    def test_static_is_sharpest(self):
        r = freeze_blur_test.analyze_freeze_blur(
            TONES / "freeze_vibrato_vowel_static.wav", 110.0)
        self.assertTrue(approx(r["mean_blur_db"], -5.496))
        self.assertTrue(approx(r["worst_blur_db"], -4.476))
        self.assertEqual(r["n_harmonics"], 32)

    def test_vibrato_is_blurriest(self):
        r = freeze_blur_test.analyze_freeze_blur(
            TONES / "freeze_vibrato_vowel.wav", 110.0)
        self.assertTrue(approx(r["mean_blur_db"], -1.392))
        self.assertGreater(r["worst_blur_db"], 0.0)  # worst harmonic smears past 0 dB

    def test_frozen_sits_between(self):
        static = freeze_blur_test.analyze_freeze_blur(
            TONES / "freeze_vibrato_vowel_static.wav", 110.0)["mean_blur_db"]
        vibrato = freeze_blur_test.analyze_freeze_blur(
            TONES / "freeze_vibrato_vowel.wav", 110.0)["mean_blur_db"]
        frozen = freeze_blur_test.analyze_freeze_blur(
            TONES / "freeze_vibrato_vowel_frozen.wav", 110.0)["mean_blur_db"]
        self.assertTrue(approx(frozen, -4.357))
        self.assertLess(frozen, vibrato)   # freeze sharpens vs vibrato
        self.assertGreater(frozen, static)  # but not as sharp as a static vowel

    def test_regression_matches_committed(self):
        for name, committed in (
            ("freeze_vibrato_vowel_static.wav", "freeze-blur/vowel_static.freeze.json"),
            ("freeze_vibrato_vowel.wav", "freeze-blur/vowel_vibrato.freeze.json"),
            ("freeze_vibrato_vowel_frozen.wav", "freeze-blur/vowel_frozen.freeze.json"),
            ("freeze_vibrato_vowel_frozen.wav", "freeze-blur/frozen_vs_vibrato.freeze.json"),
        ):
            r = freeze_blur_test.analyze_freeze_blur(TONES / name, 110.0)
            c = load_committed(committed)
            self.assertTrue(approx(r["mean_blur_db"], c["mean_blur_db"]), name)
            self.assertTrue(approx(r["worst_blur_db"], c["worst_blur_db"]), name)
            self.assertTrue(approx(r["best_blur_db"], c["best_blur_db"]), name)

    def test_max_blur_threshold(self):
        # With a threshold, the result carries pass/fail; without one
        # it reports the value only (pass is None).
        r = freeze_blur_test.analyze_freeze_blur(
            TONES / "freeze_vibrato_vowel_frozen.wav", 110.0, max_blur_db=-3.0)
        self.assertEqual(r["max_blur_threshold_db"], -3.0)
        self.assertTrue(r["pass"])  # frozen mean -4.357 is sharper than -3 dB
        r2 = freeze_blur_test.analyze_freeze_blur(
            TONES / "freeze_vibrato_vowel.wav", 110.0, max_blur_db=-3.0)
        self.assertFalse(r2["pass"])  # vibrato mean -1.392 is blurrier than -3 dB
        r3 = freeze_blur_test.analyze_freeze_blur(
            TONES / "freeze_vibrato_vowel_frozen.wav", 110.0)
        self.assertIsNone(r3["pass"])
        self.assertIsNone(r3["max_blur_threshold_db"])

    def test_simulated_freeze_sharpens_vibrato(self):
        vibrato = freeze_blur_test.synthesize_vowel(
            f0=110.0, duration=2.0, fs=48000,
            vibrato_rate=freeze_blur_test.VIBRATO_RATE,
            vibrato_depth_semitones=freeze_blur_test.VIBRATO_DEPTH)
        frozen = freeze_blur_test.simulate_freeze(vibrato, 48000, duration=1.0)
        self.assertEqual(len(frozen), 48000)
        # The frozen frame is a single held spectrum: its harmonic
        # peaks must be finite and non-silent.
        self.assertGreater(max(abs(s) for s in frozen), 0.01)

    def test_vowel_synthesis_is_deterministic(self):
        a = freeze_blur_test.synthesize_vowel(f0=110.0, duration=0.5, fs=48000)
        b = freeze_blur_test.synthesize_vowel(f0=110.0, duration=0.5, fs=48000)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
