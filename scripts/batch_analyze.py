#!/usr/bin/env python3
"""Analyze all WAV files in a folder."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_wav import analyze

def main():
    ap = argparse.ArgumentParser(description='Batch analyze WAV files into ARC-AudioBench JSON.')
    ap.add_argument('input_dir')
    ap.add_argument('--out', default='results/batch')
    args = ap.parse_args()
    inp = Path(args.input_dir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(inp.rglob('*.wav'))
    manifest = {'schema_version':'arc-audiobench-batch-v1','input_dir':str(inp),'count':len(files),'results':[]}
    for wav in files:
        res = analyze(wav)
        target = out / f'{wav.stem}.analysis.json'
        target.write_text(json.dumps(res, indent=2), encoding='utf-8')
        manifest['results'].append({'wav':str(wav),'result':str(target),'pass':res.get('pass', False)})
        print(target)
    (out/'batch_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(out/'batch_manifest.json')
if __name__ == '__main__': main()
