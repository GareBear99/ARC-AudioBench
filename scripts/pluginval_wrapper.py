#!/usr/bin/env python3
"""Optional pluginval wrapper.

This script does not bundle pluginval. It records the intended command and can run pluginval
when the binary and plugin path are provided locally.
"""
from __future__ import annotations
import argparse, subprocess, json, datetime
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pluginval', required=True, help='Path to pluginval executable')
    ap.add_argument('--plugin', required=True, help='Path to plugin binary such as VST3/AU')
    ap.add_argument('--strictness', default='10')
    ap.add_argument('--out', default='results/pluginval_result.json')
    ap.add_argument('--run', action='store_true', help='Actually execute pluginval')
    args=ap.parse_args()
    cmd=[args.pluginval, '--strictness-level', str(args.strictness), '--validate', args.plugin]
    result={'schema_version':'arc-audiobench-pluginval-v1','created_utc':datetime.datetime.utcnow().isoformat()+'Z','command':cmd,'executed':False,'returncode':None,'stdout':'','stderr':''}
    if args.run:
        p=subprocess.run(cmd, text=True, capture_output=True)
        result.update({'executed':True,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'pass':p.returncode==0})
    out=Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result, indent=2), encoding='utf-8'); print(out)
if __name__ == '__main__': main()
