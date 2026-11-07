"""Cramping test (scripts/cramping_test.py).

Measures a filter's response from a log sweep and compares it to the
analogue prototype. The headline is the error at the geometric-mean
frequency sqrt(fc * sr/2). The RBJ biquad cramps: peaking at fc 8000
loses -2.026 dB there (pass=False -- the negative control that proves
the test sees cramping), while highpass passes at +0.271 dB. The
FreeEQ8 baseline to beat is -3.383 dB at the geometric-mean frequency.
"""
from __future__ import annotations

import unittest

from helpers import TONES, approx, load_committed

import cramping_test


def run(filter_type, fc=8000.0, q=1.0, gain_db=12.0):
    name = {"peaking": "sweep_peaking_8000hz.wav",
            "lowpass": "sweep_lowpass_8000hz.wav",
            "highpass": "sweep_highpass_8000hz.wav"}[filter_type]
    return cramping_test.run_cramping(
        TONES / name, filter_type, fc, q, gain_db,
        input_amplitude=0.5, f_start=20.0, f_end=20000.0, max_error_db=1.0)


class TestCramping(unittest.TestCase):
    def test_peaking_reproduces_committed(self):
        r = run("peaking")
        self.assertFalse(r["pass"])  # RBJ cramps at 8 kHz: negative control
        self.assertTrue(approx(r["error_at_geometric_mean_db"], -2.026))
        self.assertTrue(approx(r["error_at_fc_db"], -4.011))
        self.assertTrue(approx(r["max_abs_error_db"], 4.011))
        self.assertTrue(approx(r["geometric_mean_hz"], 13856.406))
        self.assertEqual(r["schema_version"], "arc-audiobench-cramping-v1")

    def test_lowpass_reproduces_committed(self):
        r = cramping_test.run_cramping(
            TONES / "sweep_lowpass_8000hz.wav", "lowpass", 8000.0, 0.707, 12.0,
            input_amplitude=0.5, f_start=20.0, f_end=20000.0, max_error_db=1.0)
        self.assertFalse(r["pass"])
        self.assertTrue(approx(r["error_at_geometric_mean_db"], -4.201))

    def test_highpass_passes(self):
        # Committed highpass render used Q 0.707 (like lowpass).
        r = run("highpass", q=0.707)
        self.assertTrue(r["pass"])
        self.assertTrue(approx(r["error_at_geometric_mean_db"], 0.271))

    def test_regression_matches_committed(self):
        cases = (
            ("peaking", "cramping/sweep_peaking_8000hz.cramping.json", 1.0, 12.0),
            ("lowpass", "cramping/sweep_lowpass_8000hz.cramping.json", 0.707, 12.0),
            ("highpass", "cramping/sweep_highpass_8000hz.cramping.json", 0.707, 12.0),
        )
        for ftype, committed, q, gain in cases:
            name = {"peaking": "sweep_peaking_8000hz.wav",
                    "lowpass": "sweep_lowpass_8000hz.wav",
                    "highpass": "sweep_highpass_8000hz.wav"}[ftype]
            r = cramping_test.run_cramping(
                TONES / name, ftype, 8000.0, q, gain,
                input_amplitude=0.5, f_start=20.0, f_end=20000.0, max_error_db=1.0)
            c = load_committed(committed)
            self.assertEqual(r["pass"], c["pass"], ftype)
            self.assertTrue(approx(r["error_at_geometric_mean_db"],
                                   c["error_at_geometric_mean_db"]), ftype)
            self.assertTrue(approx(r["error_at_fc_db"], c["error_at_fc_db"]), ftype)

    def test_rbj_coefficients_sanity(self):
        # RBJ peaking returns (b, a): b has 3 coefficients, a has 2
        # (a0 is normalised to 1, so a = (a1, a2)).
        b, a = cramping_test.rbj_peaking(8000.0, 1.0, 12.0, 48000)
        self.assertEqual(len(b), 3)
        self.assertEqual(len(a), 2)
        # +12 dB boost: the numerator sums to more than the denominator.
        self.assertGreater(sum(b), sum(a) + 1.0)

    def test_render_reference_is_deterministic(self):
        # --render-reference renders the same sweep through the RBJ
        # biquad; two renders must be bit-identical.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "r1.wav"
            p2 = Path(td) / "r2.wav"
            for p in (p1, p2):
                rc = cramping_test.main(["--render-reference", str(p),
                                         "--type", "peaking", "--fc", "8000"])
                self.assertEqual(rc, 0)
            self.assertEqual(p1.read_bytes(), p2.read_bytes())


if __name__ == "__main__":
    unittest.main()
