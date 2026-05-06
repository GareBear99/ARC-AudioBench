#!/usr/bin/env python3
"""Compare two ARC-AudioBench result JSON files."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('baseline')
    ap.add_argument('candidate')
    ap.add_argument('--out')
    args=ap.parse_args()
    a=json.loads(Path(args.baseline).read_text(encoding='utf-8'))
    b=json.loads(Path(args.candidate).read_text(encoding='utf-8'))
    keys=['peak','rms','crest_factor','dc_offset','clipping_samples','dominant_frequency_estimate_hz']
    delta={k:{'baseline':a.get(k),'candidate':b.get(k),'delta':(b.get(k,0)-a.get(k,0)) if isinstance(a.get(k), (int,float)) and isinstance(b.get(k),(int,float)) else None} for k in keys}
    result={'schema_version':'arc-audiobench-comparison-v1','baseline':args.baseline,'candidate':args.candidate,'deltas':delta,'pass': b.get('pass', False)}
    txt=json.dumps(result, indent=2)
    if args.out:
        out=Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(txt, encoding='utf-8'); print(out)
    else:
        print(txt)
if __name__ == '__main__': main()
