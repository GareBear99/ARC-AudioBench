#!/usr/bin/env python3
from __future__ import annotations
import json, hashlib, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'release_evidence'
OUT.mkdir(exist_ok=True)

def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '.git' not in p.parts:
            files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
    manifest={
        'schema_version':'arc-audiobench-release-manifest-v1',
        'project':'ARC-AudioBench',
        'version':(ROOT/'VERSION').read_text().strip() if (ROOT/'VERSION').exists() else 'unknown',
        'created_utc':datetime.datetime.utcnow().replace(microsecond=0).isoformat()+'Z',
        'file_count':len(files),
        'files':files,
        'validation_commands':[
            'python3 scripts/generate_test_tones.py',
            'python3 scripts/analyze_wav.py data/test_tones/sine_1000hz.wav --out results/sine_1000hz.analysis.json',
            'python3 scripts/validate_results.py results/sine_1000hz.analysis.json',
            'python3 scripts/report_results.py results --out reports/index.html --markdown reports/summary.md',
            'python3 scripts/validate_repo.py'
        ]
    }
    (OUT/'ARC_AUDIOBENCH_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (OUT/'source_inventory.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
    summary={'project':'ARC-AudioBench','version':manifest['version'],'file_count':len(files),'status':'source release candidate generated'}
    (OUT/'source_audit_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(OUT/'ARC_AUDIOBENCH_RELEASE_MANIFEST.json')
if __name__ == '__main__': main()
