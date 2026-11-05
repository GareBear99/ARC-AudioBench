#!/usr/bin/env python3
"""Unified ARC-AudioBench CLI wrapper."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent

def run(script, *args):
    return subprocess.call([sys.executable, str(HERE/script), *map(str,args)])

def main():
    ap=argparse.ArgumentParser(prog='arc-audiobench')
    sub=ap.add_subparsers(dest='cmd', required=True)
    g=sub.add_parser('generate'); g.add_argument('--out', default='data/test_tones')
    a=sub.add_parser('analyze'); a.add_argument('wav'); a.add_argument('--out'); a.add_argument('--label')
    b=sub.add_parser('batch'); b.add_argument('input_dir'); b.add_argument('--out', default='results/batch')
    r=sub.add_parser('report'); r.add_argument('results'); r.add_argument('--out', default='reports/index.html'); r.add_argument('--markdown', default='reports/summary.md')
    v=sub.add_parser('validate-result'); v.add_argument('result_json')
    al=sub.add_parser('alias'); al.add_argument('wav'); al.add_argument('--f0', type=float, required=True); al.add_argument('--out'); al.add_argument('--label'); al.add_argument('--worst-alias-db', type=float, default=-60.0); al.add_argument('--asr-db', type=float, default=-40.0)
    nm=sub.add_parser('nmr'); nm.add_argument('wav'); nm.add_argument('--f0', type=float, required=True); nm.add_argument('--out'); nm.add_argument('--label'); nm.add_argument('--ref-spl', type=float, default=96.0); nm.add_argument('--nmr-db', type=float, default=0.0)
    sub.add_parser('evidence')
    sub.add_parser('validate-repo')
    args=ap.parse_args()
    if args.cmd=='generate': return run('generate_test_tones.py','--out',args.out)
    if args.cmd=='analyze':
        cmd=['analyze_wav.py', args.wav]
        if args.out: cmd += ['--out', args.out]
        if args.label: cmd += ['--label', args.label]
        return run(*cmd)
    if args.cmd=='batch': return run('batch_analyze.py', args.input_dir, '--out', args.out)
    if args.cmd=='report': return run('report_results.py', args.results, '--out', args.out, '--markdown', args.markdown)
    if args.cmd=='validate-result': return run('validate_results.py', args.result_json)
    if args.cmd=='alias':
        cmd=['alias_test.py', args.wav, '--f0', str(args.f0)]
        if args.out: cmd += ['--out', args.out]
        if args.label: cmd += ['--label', args.label]
        cmd += ['--worst-alias-db', str(args.worst_alias_db), '--asr-db', str(args.asr_db)]
        return run(*cmd)
    if args.cmd=='nmr':
        cmd=['nmr_test.py', args.wav, '--f0', str(args.f0)]
        if args.out: cmd += ['--out', args.out]
        if args.label: cmd += ['--label', args.label]
        cmd += ['--ref-spl', str(args.ref_spl), '--nmr-db', str(args.nmr_db)]
        return run(*cmd)
    if args.cmd=='evidence': return run('make_evidence_pack.py')
    if args.cmd=='validate-repo': return run('validate_repo.py')
if __name__ == '__main__': raise SystemExit(main())
