"""CLI wrapper (scripts/arc_audiobench.py).

The single entry point must expose every measurement subcommand and
run end to end in a scratch directory: generate -> analyze -> alias /
nmr / cramping / stoi / freeze-blur -> report -> evidence ->
validate-repo.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, TONES

CLI = ROOT / "scripts" / "arc_audiobench.py"


def cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True, text=True, cwd=cwd or ROOT)


class TestCli(unittest.TestCase):
    def test_help_lists_all_measurements(self):
        proc = cli("--help")
        self.assertEqual(proc.returncode, 0)
        for sub in ("generate", "analyze", "batch", "report",
                    "validate-result", "alias", "nmr", "cramping",
                    "stoi", "freeze-blur", "evidence", "validate-repo"):
            self.assertIn(sub, proc.stdout, sub)

    def test_generate_and_analyze_in_scratch(self):
        with tempfile.TemporaryDirectory() as td:
            tones = Path(td) / "tones"
            proc = cli("generate", "--out", str(tones))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((tones / "sine_1000hz.wav").exists())
            out = Path(td) / "a.json"
            proc = cli("analyze", str(tones / "sine_1000hz.wav"), "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            d = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(d["schema_version"], "arc-audiobench-result-v1")
            self.assertTrue(d["pass"])

    def test_measurement_subcommands_in_scratch(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "o.json"
            proc = cli("alias", str(TONES / "sawtooth_bandlimited_997hz.wav"),
                       "--f0", "997", "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(json.loads(out.read_text(encoding="utf-8"))["pass"])
            proc = cli("nmr", str(TONES / "sawtooth_bandlimited_997hz.wav"),
                       "--f0", "997", "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            proc = cli("stoi", str(TONES / "stoi_speech_like.wav"),
                       str(TONES / "stoi_speech_like_vocoded.wav"),
                       "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertAlmostEqual(
                json.loads(out.read_text(encoding="utf-8"))["stoi"], 0.4807)
            proc = cli("freeze-blur",
                       str(TONES / "freeze_vibrato_vowel_frozen.wav"),
                       "--f0", "110", "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            proc = cli("cramping", str(TONES / "sweep_highpass_8000hz.wav"),
                       "--type", "highpass", "--fc", "8000", "--q", "0.707",
                       "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(json.loads(out.read_text(encoding="utf-8"))["pass"])

    def test_validate_repo_passes(self):
        proc = cli("validate-repo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("validation OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
