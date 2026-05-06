#!/usr/bin/env python3
"""Generate HTML/Markdown reports from ARC-AudioBench result JSON files."""
from __future__ import annotations
import argparse, json, html, datetime
from pathlib import Path

def collect(path: Path):
    files = sorted(path.rglob('*.json')) if path.is_dir() else [path]
    rows=[]
    for p in files:
        try:
            data=json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        if data.get('schema_version') == 'arc-audiobench-result-v1':
            rows.append((p,data))
    return rows

def html_report(rows):
    trs=[]
    for p,d in rows:
        status='PASS' if d.get('pass') else 'CHECK'
        trs.append(f"<tr><td>{html.escape(d.get('label', p.stem))}</td><td>{status}</td><td>{d.get('sample_rate')}</td><td>{d.get('duration_seconds')}</td><td>{d.get('peak')}</td><td>{d.get('rms')}</td><td>{d.get('dc_offset')}</td><td>{d.get('clipping_samples')}</td><td><code>{html.escape(str(p))}</code></td></tr>")
    body=''.join(trs)
    created=datetime.datetime.utcnow().isoformat()+'Z'
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>ARC-AudioBench Report</title><style>body{{font-family:system-ui;background:#0b1020;color:#e8ecff;padding:32px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #2b345f;padding:8px}}th{{background:#151d3c}}code{{color:#8ee6ff}}</style></head><body><h1>ARC-AudioBench Report</h1><p>Generated {created}</p><table><thead><tr><th>Label</th><th>Status</th><th>SR</th><th>Duration</th><th>Peak</th><th>RMS</th><th>DC</th><th>Clip</th><th>File</th></tr></thead><tbody>{body}</tbody></table></body></html>"""

def md_report(rows):
    out=['# ARC-AudioBench Report','', '| Label | Status | SR | Duration | Peak | RMS | DC | Clip |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p,d in rows:
        out.append(f"| {d.get('label', p.stem)} | {'PASS' if d.get('pass') else 'CHECK'} | {d.get('sample_rate')} | {d.get('duration_seconds')} | {d.get('peak')} | {d.get('rms')} | {d.get('dc_offset')} | {d.get('clipping_samples')} |")
    return '\n'.join(out)+'\n'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('results')
    ap.add_argument('--out', default='reports/index.html')
    ap.add_argument('--markdown')
    args=ap.parse_args()
    rows=collect(Path(args.results))
    out=Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(html_report(rows), encoding='utf-8')
    print(out)
    if args.markdown:
        md=Path(args.markdown); md.parent.mkdir(parents=True, exist_ok=True); md.write_text(md_report(rows), encoding='utf-8'); print(md)
if __name__ == '__main__': main()
