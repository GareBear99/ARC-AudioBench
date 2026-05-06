#!/usr/bin/env python3
from pathlib import Path
import json, ast
ROOT=Path(__file__).resolve().parents[1]
required=[
 'README.md','QUICKSTART.md','BENCHMARKS.md','CITATION.cff','pyproject.toml','VERSION',
 'scripts/generate_test_tones.py','scripts/analyze_wav.py','scripts/batch_analyze.py','scripts/report_results.py','scripts/validate_results.py','scripts/compare_outputs.py','scripts/pluginval_wrapper.py','scripts/make_evidence_pack.py','scripts/arc_audiobench.py',
 'schemas/audio_bench_result.schema.json','config/default_thresholds.json','docs/SEO_KEYWORD_MAP.md','docs/FREEEQ8_INTEGRATION.md','docs/FREEVOX8_INTEGRATION.md','docs/RESEARCH_CITATION_LAYER.md','docs/PUBLIC_LAUNCH_PLAN.md','docs/COMPETITIVE_POSITIONING.md','docs/DAW_SMOKE_TEST_MATRIX.md','docs/FREEEQ8_BENCHMARK_SUITE.md','docs/ECOSYSTEM_REPO_REFERENCES.md','docs/FREEVOX8_BENCHMARK_SUITE.md',
 '.github/workflows/validate.yml','.github/ISSUE_TEMPLATE/plugin_benchmark.yml'
]
missing=[p for p in required if not (ROOT/p).exists()]
if missing: raise SystemExit('Missing required files: '+', '.join(missing))
for jp in ['data/integration_targets.json','data/seo_keywords.json','schemas/audio_bench_result.schema.json','config/default_thresholds.json']:
    json.loads((ROOT/jp).read_text(encoding='utf-8'))
for py in (ROOT/'scripts').glob('*.py'):
    ast.parse(py.read_text(encoding='utf-8'))
readme=(ROOT/'README.md').read_text(encoding='utf-8').lower()
for term in ['audio plugin benchmark','juce plugin testing','freeeq8','freevox8','python audio analysis','reproducible audio research','arc-neuron','arc-core','arc-rar','omnibinary','awesome audio plugins']:
    if term not in readme:
        raise SystemExit(f'Missing SEO term in README: {term}')

targets=json.loads((ROOT/'data/integration_targets.json').read_text(encoding='utf-8'))
required_repos=['FreeEQ8','FreeVox8','Voxel Audio','ARC-Neuron LLMBuilder','ARC-Core','Arc-RAR','OmniBinary Runtime','Awesome Audio Plugins & Dev','Awesome Audio Lists','Awesome Music Platforms','Awesome Python Audio Science','TizWildinEntertainmentHUB','TizWildin Release Vault','Instrudio']
found={t.get('name') for t in targets}
missing_repos=[r for r in required_repos if r not in found]
if missing_repos:
    raise SystemExit('Missing ecosystem repo references: '+', '.join(missing_repos))

print('ARC-AudioBench validation OK')
