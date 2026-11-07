"""CLI-level regression: run each measurement script as a subprocess
and check the exit code plus the headline numbers against the
committed results. This pins the command-line behaviour, not just the
imported functions.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, TONES, approx, load_committed

SCRIPTS = ROOT / "scripts"


def run_cli(script, *args):
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.json"
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args, "--out", str(out)],
            capture_output=True, text=True, cwd=ROOT)
        data = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
        return proc.returncode, data, proc.stderr


class TestCliRegression(unittest.TestCase):
    def test_alias_cli_exit_codes(self):
        rc, r, _ = run_cli("alias_test.py",
                           str(TONES / "sawtooth_bandlimited_997hz.wav"), "--f0", "997")
        self.assertEqual(rc, 0)
        self.assertTrue(r["pass"])
        rc, r, _ = run_cli("alias_test.py",
                           str(TONES / "sawtooth_naive_997hz.wav"), "--f0", "997")
        self.assertEqual(rc, 1)  # naive fails: negative control
        self.assertFalse(r["pass"])

    def test_nmr_cli_exit_codes(self):
        rc, r, _ = run_cli("nmr_test.py",
                           str(TONES / "sawtooth_bandlimited_997hz.wav"), "--f0", "997")
        self.assertEqual(rc, 0)
        self.assertTrue(r["pass"])
        rc, r, _ = run_cli("nmr_test.py",
                           str(TONES / "sawtooth_naive_997hz.wav"), "--f0", "997")
        self.assertEqual(rc, 1)
        self.assertTrue(approx(r["worst_nmr_db"], 36.046))

    def test_cramping_cli_exit_code(self):
        rc, r, _ = run_cli("cramping_test.py",
                           str(TONES / "sweep_peaking_8000hz.wav"),
                           "--type", "peaking", "--fc", "8000", "--q", "1.0",
                           "--gain-db", "12.0")
        self.assertEqual(rc, 1)  # RBJ cramps: negative control
        self.assertTrue(approx(r["error_at_geometric_mean_db"], -2.026))

    def test_stoi_cli(self):
        rc, r, _ = run_cli("stoi_test.py",
                           str(TONES / "stoi_speech_like.wav"),
                           str(TONES / "stoi_speech_like_vocoded.wav"))
        self.assertEqual(rc, 0)
        self.assertTrue(approx(r["stoi"], 0.4807))

    def test_stoi_cli_min_threshold(self):
        rc, r, _ = run_cli("stoi_test.py",
                           str(TONES / "stoi_speech_like.wav"),
                           str(TONES / "stoi_speech_like_vocoded.wav"),
                           "--min-stoi", "0.7434")
        self.assertEqual(rc, 1)  # synthetic vocoded tone is below the TAL bar
        self.assertFalse(r["pass"])

    def test_freeze_cli(self):
        rc, r, _ = run_cli("freeze_blur_test.py",
                           str(TONES / "freeze_vibrato_vowel_frozen.wav"),
                           "--f0", "110",
                           "--compare", str(TONES / "freeze_vibrato_vowel.wav"))
        self.assertEqual(rc, 0)
        self.assertTrue(approx(r["mean_blur_db"], -4.357))
        self.assertIn("comparison", r)

    def test_freeze_cli_max_blur_threshold(self):
        rc, r, _ = run_cli("freeze_blur_test.py",
                           str(TONES / "freeze_vibrato_vowel.wav"),
                           "--f0", "110", "--max-blur-db", "-3.0")
        self.assertEqual(rc, 1)  # vibrato mean -1.392 is blurrier than -3 dB
        self.assertFalse(r["pass"])

    def test_committed_results_are_valid_json(self):
        # Every committed measurement result parses and carries its schema.
        for rel in (
            "alias/sawtooth_bandlimited_997hz.alias.json",
            "alias/sawtooth_naive_997hz.alias.json",
            "nmr/sawtooth_bandlimited_997hz.nmr.json",
            "nmr/sawtooth_naive_997hz.nmr.json",
            "nmr/therum_mipped_997hz.nmr.json",
            "nmr/therum_naive_997hz.nmr.json",
            "cramping/sweep_peaking_8000hz.cramping.json",
            "cramping/sweep_lowpass_8000hz.cramping.json",
            "cramping/sweep_highpass_8000hz.cramping.json",
            "stoi/speech_like_vs_clean.stoi.json",
            "stoi/speech_like_vs_noisy0db.stoi.json",
            "stoi/speech_like_vs_vocoded.stoi.json",
            "freeze-blur/vowel_static.freeze.json",
            "freeze-blur/vowel_vibrato.freeze.json",
            "freeze-blur/vowel_frozen.freeze.json",
            "freeze-blur/frozen_vs_vibrato.freeze.json",
        ):
            d = load_committed(rel)
            self.assertIn("schema_version", d, rel)
            self.assertEqual(d["tool"], "ARC-AudioBench", rel)


if __name__ == "__main__":
    unittest.main()
