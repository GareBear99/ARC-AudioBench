# ARC-AudioBench

> **Local-first benchmark suite for audio plugins, DSP tools, JUCE projects, spectral processors, Web Audio instruments, and AI-assisted music software.**

![Status](https://img.shields.io/badge/status-v1.0.0--rc1-blue)
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

## Ecosystem anchors

| Project | Role in ARC-AudioBench |
|---|---|
| [FreeEQ8](https://github.com/GareBear99/FreeEQ8) | flagship EQ validation target |
| [FreeVox8](https://github.com/GareBear99/FreeVox8) | spectral vocoder / ghost resynthesis benchmark target |
| [Voxel Audio](https://github.com/GareBear99/Voxel_Audio) | visual/export/audio-render benchmark target |
| [ARC-Neuron LLMBuilder](https://github.com/GareBear99/ARC-Neuron-LLMBuilder) | governance/evidence/promotion model reference |
| [ARC-Core](https://github.com/GareBear99/ARC-Core) | receipt, validation, release authority reference |
| [Arc-RAR](https://github.com/GareBear99/Arc-RAR) | archival/evidence bundle direction |
| [OmniBinary Runtime](https://github.com/GareBear99/omnibinary-runtime) | binary truth / replay ledger direction |
| [Awesome Audio Plugins & Dev](https://github.com/GareBear99/awesome-audio-plugins-dev) | Start Here list and public discovery route |
| [Awesome Python Audio Science](https://github.com/GareBear99/awesome-python-audio-science) | research/academic SEO bridge |

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

This package is a **v1.0.0 release candidate source package**. The local benchmark, report, validation, and evidence scripts run without external services. Plugin-specific certification still requires the actual plugin binaries, pluginval output, and DAW smoke tests for each target plugin.

## License

MIT. See `LICENSE`.
