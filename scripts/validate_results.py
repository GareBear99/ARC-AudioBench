#!/usr/bin/env python3
"""Validate ARC-AudioBench JSON results against schema-lite and thresholds."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def load_thresholds(path: str | None) -> dict:
    default = Path(__file__).resolve().parents[1] / 'config' / 'default_thresholds.json'
    p = Path(path) if path else default
    return json.loads(p.read_text(encoding='utf-8'))

def validate_result(result: dict, thresholds: dict) -> list[str]:
    errors=[]
    required=['schema_version','tool','analysis_type','source_file','sha256','sample_rate','duration_seconds','peak','rms','dc_offset','clipping_samples']
    for k in required:
        if k not in result:
            errors.append(f'missing {k}')
    if result.get('schema_version') != 'arc-audiobench-result-v1':
        errors.append('wrong schema_version')
    if result.get('peak',0) > thresholds.get('max_peak',1.0):
        errors.append(f"peak exceeds threshold: {result.get('peak')}")
    if abs(result.get('dc_offset',0)) > thresholds.get('max_abs_dc_offset',0.01):
        errors.append(f"dc offset exceeds threshold: {result.get('dc_offset')}")
    if result.get('clipping_samples',0) > thresholds.get('max_clipping_samples',0):
        errors.append(f"clipping samples exceed threshold: {result.get('clipping_samples')}")
    if result.get('duration_seconds',0) < thresholds.get('min_duration_seconds',0.001):
        errors.append('duration too short')
    return errors

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('result_json')
    ap.add_argument('--thresholds')
    args=ap.parse_args()
    result=json.loads(Path(args.result_json).read_text(encoding='utf-8'))
    thresholds=load_thresholds(args.thresholds)
    errors=validate_result(result, thresholds)
    if errors:
        for e in errors: print('ERROR:', e)
        raise SystemExit(1)
    print('ARC-AudioBench result validation OK:', args.result_json)
if __name__ == '__main__': main()
