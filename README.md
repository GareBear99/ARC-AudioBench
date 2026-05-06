# ARC-AudioBench

> **Local-first benchmark suite for audio plugins, DSP tools, JUCE projects, spectral processors, Web Audio instruments, and AI-assisted music software.**

![Status](https://img.shields.io/badge/status-v1.0.0-public%20source%20release-brightgreen)
![Python](https://img.shields.io/badge/python-3.9%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-green)
![Audio DSP](https://img.shields.io/badge/audio-DSP%20benchmark-ff69b4)
![JUCE](https://img.shields.io/badge/JUCE-plugin%20testing-orange)

**ARC-AudioBench** is the validation and evidence layer for open-source audio software. It generates deterministic test signals, analyzes rendered WAV output, compares benchmark runs, validates JSON results, builds release evidence packs, and documents pluginval/DAW validation paths for projects like **FreeEQ8**, **FreeVox8**, **Voxel Audio**, and future ARC/TizWildin audio tools.

## Quick answer

Use this repo if you need a searchable, reproducible benchmark suite for:

- audio plugin benchmark workflows
- JUCE plugin testing
- VST3 / AU validation planning
- DSP regression tests
- spectral processor testing
- FreeEQ8 and FreeVox8 validation
- Python audio analysis
- pluginval evidence collection
- reproducible audio research
- citation-ready audio software reports

## Why it exists

Audio projects often claim they are stable, high quality, realtime safe, or production ready. ARC-AudioBench makes those claims easier to prove with repeatable files:

```text
test signal -> plugin/render path -> WAV analysis -> JSON result -> threshold validation -> evidence pack
```

This repo is intentionally **local-first**. No cloud service is required to generate test tones, analyze WAVs, compare outputs, or produce evidence.

## Features

- Deterministic WAV test tone generation
- Sine tones, silence, impulse, and log sweep generation
- WAV analysis: peak, RMS, crest factor, DC offset, clipping, zero-crossing frequency estimate, SHA-256
- Batch analysis for folders of WAV files
- Result validation against thresholds
- Result comparison and delta reporting
- HTML + Markdown report generation
- JSON schema for benchmark output
- Evidence pack generation for releases
- FreeEQ8 integration notes
- FreeVox8 spectral-vocoder benchmark plan
- Voxel Audio visual/export benchmark plan
- ARC governance and receipt-style release evidence
- Citation metadata and research SEO documentation

## Start here

```bash
python3 scripts/generate_test_tones.py
python3 scripts/analyze_wav.py data/test_tones/sine_1000hz.wav --out results/sine_1000hz.analysis.json
python3 scripts/validate_results.py results/sine_1000hz.analysis.json
python3 scripts/report_results.py results --out reports/index.html --markdown reports/summary.md
python3 scripts/make_evidence_pack.py
```

Or use the single CLI wrapper:

```bash
python3 scripts/arc_audiobench.py generate
python3 scripts/arc_audiobench.py analyze data/test_tones/sine_1000hz.wav --out results/sine_1000hz.analysis.json
python3 scripts/arc_audiobench.py report results --out reports/index.html
python3 scripts/arc_audiobench.py evidence
python3 scripts/arc_audiobench.py validate-repo
```

## Repository map

```text
ARC-AudioBench/
├─ README.md
├─ QUICKSTART.md
├─ BENCHMARKS.md
├─ CITATION.cff
├─ pyproject.toml
├─ docs/
├─ scripts/
├─ schemas/
├─ data/
├─ examples/
├─ results/
├─ reports/
├─ integrations/
├─ release_evidence/
├─ assets/
└─ .github/
```

## Ecosystem anchors and source references

ARC-AudioBench is a standalone benchmark product, but it was intentionally designed from the public **GareBear99 / TizWildin** repo ecosystem. These are the canonical repos referenced by the benchmark suite, documentation, SEO map, release-evidence model, and future integration path.

| Repository | Role in ARC-AudioBench | Category |
|---|---|---|
| [FreeEQ8](https://github.com/GareBear99/FreeEQ8) | Primary open-source JUCE/C++ parametric EQ benchmark target | `product-anchor` |
| [FreeVox8](https://github.com/GareBear99/FreeVox8) | Spectral vocoder / ghost-resynthesis benchmark target | `product-anchor` |
| [Voxel Audio](https://github.com/GareBear99/Voxel_Audio) | Visualizer/export integrity and browser audio-output benchmark target | `product-anchor` |
| [ARC-Neuron LLMBuilder](https://github.com/GareBear99/ARC-Neuron-LLMBuilder) | Governed local AI evidence, promotion, benchmark language, and release-gate reference | `governance-reference` |
| [ARC-Core](https://github.com/GareBear99/ARC-Core) | Authority, receipts, validation, release-gate, and evidence-control reference | `governance-reference` |
| [Arc-RAR](https://github.com/GareBear99/Arc-RAR) | Archival bundle, rollback, evidence-pack, and replay package reference | `governance-reference` |
| [OmniBinary Runtime](https://github.com/GareBear99/omnibinary-runtime) | Binary truth / replay ledger / restore path reference | `governance-reference` |
| [Awesome Audio Plugins & Dev](https://github.com/GareBear99/awesome-audio-plugins-dev) | Start Here technical discovery list for audio plugins, DSP, JUCE, sample packs, and developer resources | `seo-discovery` |
| [Awesome Audio Lists](https://github.com/GareBear99/awesome-audio-lists) | Root hub for audio lists, submission surfaces, plugin directories, sample-pack directories, and ecosystem routing | `seo-discovery` |
| [Awesome Music Platforms](https://github.com/GareBear99/awesome-music-platforms) | Independent artist platform map for distribution, beat selling, sample packs, sync, promotion, and analytics | `seo-discovery` |
| [Awesome Python Audio Science](https://github.com/GareBear99/awesome-python-audio-science) | Academic/research-facing Python audio science, MIR, ML-audio, reproducible research, and citation bridge | `research-seo` |
| [TizWildinEntertainmentHUB](https://github.com/GareBear99/TizWildinEntertainmentHUB) | Public .io/HUB router for plugins, lists, deconstructed loops, sample packs, visualizers, and release surfaces | `public-router` |
| [TizWildin Release Vault](https://github.com/GareBear99/TizWildin-Release-Vault) | Release surface for deconstructed loops, packs, music drops, and creator-resource routing | `public-router` |
| [Instrudio](https://github.com/GareBear99/Instrudio) | SSOT Web Audio virtual-instrument runtime and physical-modeling research anchor | `research-product-anchor` |

See [`docs/ECOSYSTEM_REPO_REFERENCES.md`](docs/ECOSYSTEM_REPO_REFERENCES.md) and [`data/integration_targets.json`](data/integration_targets.json) for the machine-readable version of this map.

## High-value search terms

ARC-AudioBench is intentionally positioned around terms people actually search:

```text
audio plugin benchmark
JUCE plugin testing
VST3 validation
pluginval automation
DSP benchmark
Python audio analysis
reproducible audio research
open source audio plugin testing
FreeEQ8 benchmark
FreeVox8 spectral vocoder benchmark
```

## Honest production status

This package is a **v1.0.0 public source release framework**. The local benchmark, report, validation, and evidence scripts run without external services. Plugin-specific certification still requires the actual plugin binaries, pluginval output, and DAW smoke tests for each target plugin.

## License

MIT. See `LICENSE`.
