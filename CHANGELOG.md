# Changelog

## Unreleased — Testing grounds

- Added the test suite (`tests/`, 49 tests, 0 failures): every measurement pinned to committed results, with negative controls (naive sawtooth must fail alias + NMR, RBJ peaking sweep must fail cramping).
- Added Therum integration tests: alias + NMR re-run on the real Therum wavetable renders (mipped worst alias -45.80 dBFS at 22078 Hz, worst NMR +23.31 dB; naive -32.24 dBFS, +42.04 dB), skipped when the Therum repo is absent.
- Added pass/fail thresholds to STOI (`--min-stoi`, TAL-Vocoder bar 0.7434) and freeze-blur (`--max-blur-db`); both report the value only when no threshold is given. CLI wrapper passes both flags through.
- Added JSON Schema contracts for all five measurement result types (`schemas/*_result.schema.json`) and schema conformance tests.
- Added the measurement thresholds + reference bars to `config/default_thresholds.json` (section `measurements`): alias, NMR, cramping (FreeEQ8 baseline -3.383 dB), STOI (TAL bar 0.7434, Ghost 0.7939 / 0.7796), freeze-blur.
- Wired the NMR, cramping, STOI, and freeze-blur measurements plus the full test suite into CI (`.github/workflows/validate.yml`).
- Repo validator now requires the test suite, the five measurement schemas, and the measurements thresholds.
- Regenerated the committed STOI + freeze-blur results with the new threshold fields (values unchanged).

## v0.1.0 — Initial production source package

- Created ARC-AudioBench as a standalone benchmark/research-evidence repo.
- Added functional tone generation, WAV analysis, schema validation, and evidence packaging scripts.
- Added FreeEQ8, FreeVox8, Voxel Audio, ARC-Neuron, ARC-Core, Arc-RAR, and OmniBinary integration anchors.
- Added SEO, research, pluginval, citation, and release-evidence docs.

## 1.0.1 - Ecosystem reference completion

- Added full GareBear99 / TizWildin repository reference map.
- Expanded README ecosystem anchors with all source/reference repos used by ARC-AudioBench.
- Added `docs/ECOSYSTEM_REPO_REFERENCES.md`.
- Expanded `data/integration_targets.json` with product, governance, SEO, research, and router categories.
- Updated release evidence manifest to include referenced public repositories.
