"""STOI test (scripts/stoi_test.py) -- Taal et al. 2011.

Objective intelligibility of a degraded signal vs a clean reference.
Ordering must hold on the committed synthetic corpus: clean vs clean
is 1.0, clean vs 0 dB noise is 0.3151, clean vs the 8-band vocoder-like
degradation is 0.4807. The TAL-Vocoder bar (0.7434) is the reference
the real Ghost outputs are judged against (FreeVox8 Ghost 0.7939,
Vox8 Ghost 0.7796); the synthetic tones here are not Ghost outputs
and are pinned by value, not by the TAL bar.
"""
from __future__ import annotations

import unittest

from helpers import TONES, approx, load_committed

import stoi_test

CLEAN = "stoi_speech_like.wav"
NOISY = "stoi_speech_like_noisy0db.wav"
VOCODED = "stoi_speech_like_vocoded.wav"


class TestStoi(unittest.TestCase):
    def test_clean_vs_clean_is_one(self):
        r = stoi_test.run_stoi(TONES / CLEAN, TONES / CLEAN)
        self.assertAlmostEqual(r["stoi"], 1.0, places=4)
        self.assertEqual(r["frames_total"], 210)
        self.assertEqual(r["frames_kept"], 210)

    def test_ordering_noisy_below_vocoded_below_clean(self):
        noisy = stoi_test.run_stoi(TONES / CLEAN, TONES / NOISY)["stoi"]
        vocoded = stoi_test.run_stoi(TONES / CLEAN, TONES / VOCODED)["stoi"]
        self.assertLess(noisy, vocoded)
        self.assertLess(vocoded, 1.0)

    def test_regression_matches_committed(self):
        for name, committed in (
            (CLEAN, "stoi/speech_like_vs_clean.stoi.json"),
            (NOISY, "stoi/speech_like_vs_noisy0db.stoi.json"),
            (VOCODED, "stoi/speech_like_vs_vocoded.stoi.json"),
        ):
            r = stoi_test.run_stoi(TONES / CLEAN, TONES / name)
            c = load_committed(committed)
            self.assertTrue(approx(r["stoi"], c["stoi"]), name)
            self.assertEqual(r["frames_total"], c["frames_total"], name)
            self.assertEqual(r["frames_kept"], c["frames_kept"], name)

    def test_min_stoi_threshold(self):
        # With a threshold, the result carries pass/fail; without one
        # it reports the value only (pass is None).
        r = stoi_test.run_stoi(TONES / CLEAN, TONES / VOCODED, min_stoi=0.7434)
        self.assertEqual(r["min_stoi_threshold"], 0.7434)
        self.assertFalse(r["pass"])  # synthetic vocoded tone is below the TAL bar
        r2 = stoi_test.run_stoi(TONES / CLEAN, TONES / CLEAN, min_stoi=0.7434)
        self.assertTrue(r2["pass"])
        r3 = stoi_test.run_stoi(TONES / CLEAN, TONES / VOCODED)
        self.assertIsNone(r3["pass"])
        self.assertIsNone(r3["min_stoi_threshold"])

    def test_band_centres(self):
        # STOI uses 15 one-third-octave bands from 150 Hz to ~3.8 kHz.
        centres = stoi_test.band_centres()
        self.assertEqual(len(centres), 15)
        self.assertAlmostEqual(centres[0], 150.0, places=1)
        self.assertGreater(centres[-1], 3000.0)
        self.assertLess(centres[-1], 5000.0)

    def test_synthetic_generator_is_deterministic(self):
        a = stoi_test.generate_speech_like(duration=1.0, fs=10000, seed=42)
        b = stoi_test.generate_speech_like(duration=1.0, fs=10000, seed=42)
        self.assertEqual(a, b)
        c = stoi_test.generate_speech_like(duration=1.0, fs=10000, seed=43)
        self.assertNotEqual(a, c)

    def test_sample_rate_mismatch_raises(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "other.wav"
            sig = stoi_test.generate_speech_like(duration=0.5, fs=10000, seed=1)
            stoi_test.write_wav(p, sig, 8000)  # wrong rate on purpose
            with self.assertRaises(ValueError):
                stoi_test.run_stoi(TONES / CLEAN, p)


if __name__ == "__main__":
    unittest.main()
