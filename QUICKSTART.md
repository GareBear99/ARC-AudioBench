# ARC-AudioBench Quickstart

## 1. Generate deterministic test signals

```bash
python3 scripts/generate_test_tones.py
```

Generated files appear in `data/test_tones/`.

## 2. Analyze one WAV

```bash
python3 scripts/analyze_wav.py data/test_tones/sine_1000hz.wav --out results/sine_1000hz.analysis.json
```

## 3. Validate the result

```bash
python3 scripts/validate_results.py results/sine_1000hz.analysis.json
```

## 4. Analyze a whole folder

```bash
python3 scripts/batch_analyze.py data/test_tones --out results/batch
```

## 5. Generate reports

```bash
python3 scripts/report_results.py results --out reports/index.html --markdown reports/summary.md
```

## 6. Make release evidence

```bash
python3 scripts/make_evidence_pack.py
```

## 7. Validate the whole repo

```bash
python3 scripts/validate_repo.py
```

## CLI wrapper

```bash
python3 scripts/arc_audiobench.py generate
python3 scripts/arc_audiobench.py batch data/test_tones --out results/batch
python3 scripts/arc_audiobench.py report results --out reports/index.html
python3 scripts/arc_audiobench.py evidence
```
