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

## 6. Alias test (Therum section 7 headline test)

```bash
python3 scripts/alias_test.py data/test_tones/sawtooth_bandlimited_997hz.wav --f0 997 --out results/alias/sawtooth_bandlimited_997hz.alias.json
```

Use a fundamental that does not divide the sample rate (997 Hz, not
1000 Hz) so folded aliases land at non-harmonic frequencies. The naive
sawtooth must FAIL this test (it is the negative control); the
band-limited one must PASS. See `docs/DSP_TEST_DESIGN.md`.

## 7. Make release evidence

```bash
python3 scripts/make_evidence_pack.py
```

## 8. Validate the whole repo

```bash
python3 scripts/validate_repo.py
```

## CLI wrapper

```bash
python3 scripts/arc_audiobench.py generate
python3 scripts/arc_audiobench.py batch data/test_tones --out results/batch
python3 scripts/arc_audiobench.py alias data/test_tones/sawtooth_bandlimited_997hz.wav --f0 997 --out results/alias/sawtooth_bandlimited_997hz.alias.json
python3 scripts/arc_audiobench.py report results --out reports/index.html
python3 scripts/arc_audiobench.py evidence
```
