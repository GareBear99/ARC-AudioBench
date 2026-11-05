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
    cr=sub.add_parser('cramping'); cr.add_argument('wav'); cr.add_argument('--type', dest='filter_type', default='peaking', choices=['peaking','lowpass','highpass']); cr.add_argument('--fc', type=float, default=8000.0); cr.add_argument('--q', type=float, default=1.0); cr.add_argument('--gain-db', type=float, default=12.0); cr.add_argument('--out'); cr.add_argument('--max-error-db', type=float, default=1.0); cr.add_argument('--reference'); cr.add_argument('--input-amplitude', type=float, default=0.5); cr.add_argument('--f-start', type=float, default=20.0); cr.add_argument('--f-end', type=float, default=20000.0)
    st=sub.add_parser('stoi'); st.add_argument('clean'); st.add_argument('degraded'); st.add_argument('--out')
    fb=sub.add_parser('freeze-blur'); fb.add_argument('wav'); fb.add_argument('--f0', type=float, default=110.0); fb.add_argument('--fft-size', type=int, default=4096); fb.add_argument('--compare'); fb.add_argument('--out')
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
    if args.cmd=='cramping':
        cmd=['cramping_test.py', args.wav, '--type', args.filter_type,
             '--fc', str(args.fc), '--q', str(args.q), '--gain-db', str(args.gain_db),
             '--max-error-db', str(args.max_error_db),
             '--input-amplitude', str(args.input_amplitude),
             '--f-start', str(args.f_start), '--f-end', str(args.f_end)]
        if args.out: cmd += ['--out', args.out]
        if args.reference: cmd += ['--reference', args.reference]
        return run(*cmd)
    if args.cmd=='stoi':
        cmd=['stoi_test.py', args.clean, args.degraded]
        if args.out: cmd += ['--out', args.out]
        return run(*cmd)
    if args.cmd=='freeze-blur':
        cmd=['freeze_blur_test.py', args.wav, '--f0', str(args.f0),
             '--fft-size', str(args.fft_size)]
        if args.compare: cmd += ['--compare', args.compare]
        if args.out: cmd += ['--out', args.out]
        return run(*cmd)
    if args.cmd=='evidence': return run('make_evidence_pack.py')
    if args.cmd=='validate-repo': return run('validate_repo.py')
if __name__ == '__main__': raise SystemExit(main())
