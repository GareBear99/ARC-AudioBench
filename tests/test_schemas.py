"""Measurement result schemas (schemas/*_result.schema.json).

Each measurement type has a JSON Schema contract (draft 2020-12) and
every committed result must carry its schema_version plus the
required keys with the right types. This is a schema-lite conformance
check in stdlib only (no jsonschema dependency): it verifies the
schema files parse, declare their required keys, and that the
committed results satisfy them.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from helpers import RESULTS, ROOT

SCHEMAS = ROOT / "schemas"

# schema file -> (committed result, required keys, key -> expected type)
CASES = (
    ("alias_result.schema.json",
     "alias/sawtooth_bandlimited_997hz.alias.json",
     {"schema_version": str, "tool": str, "analysis_type": str,
      "source_file": str, "sample_rate": int, "fundamental_hz": float,
      "pass": bool, "alias_peak_count": int}),
    ("nmr_result.schema.json",
     "nmr/sawtooth_naive_997hz.nmr.json",
     {"schema_version": str, "tool": str, "analysis_type": str,
      "source_file": str, "sample_rate": int, "fundamental_hz": float,
      "pass": bool, "worst_nmr_db": float, "nmr_threshold_db": float}),
    ("cramping_result.schema.json",
     "cramping/sweep_peaking_8000hz.cramping.json",
     {"schema_version": str, "tool": str, "analysis_type": str,
      "input": str, "sample_rate_hz": int, "pass": bool,
      "error_at_geometric_mean_db": float, "max_abs_error_db": float,
      "points": list}),
    ("stoi_result.schema.json",
     "stoi/speech_like_vs_vocoded.stoi.json",
     {"schema_version": str, "tool": str, "analysis_type": str,
      "clean": str, "degraded": str, "sample_rate_hz": int,
      "stoi": float, "frames_total": int, "frames_kept": int}),
    ("freeze_blur_result.schema.json",
     "freeze-blur/frozen_vs_vibrato.freeze.json",
     {"schema_version": str, "tool": str, "analysis_type": str,
      "input": str, "f0_hz": float, "sample_rate_hz": int,
      "mean_blur_db": float, "worst_blur_db": float, "n_harmonics": int}),
)


class TestSchemas(unittest.TestCase):
    def test_schema_files_parse_and_declare_required(self):
        for schema_name, _, required in CASES:
            p = SCHEMAS / schema_name
            self.assertTrue(p.exists(), schema_name)
            schema = json.loads(p.read_text(encoding="utf-8"))
            self.assertIn("required", schema, schema_name)
            for key in required:
                self.assertIn(key, schema["required"], f"{schema_name}: {key}")

    def test_committed_results_satisfy_schemas(self):
        for schema_name, result_rel, required in CASES:
            result = json.loads((RESULTS / result_rel).read_text(encoding="utf-8"))
            schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
            self.assertEqual(result["schema_version"],
                             schema["properties"]["schema_version"]["const"],
                             result_rel)
            for key, typ in required.items():
                self.assertIn(key, result, f"{result_rel}: {key}")
                value = result[key]
                self.assertIsInstance(value, typ, f"{result_rel}: {key} is {type(value)}")
            self.assertEqual(result["tool"], "ARC-AudioBench", result_rel)


if __name__ == "__main__":
    unittest.main()
