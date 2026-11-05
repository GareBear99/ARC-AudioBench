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

## 7. NMR test (Therum section 7 acceptance test)

```bash
python3 scripts/nmr_test.py data/test_tones/sawtooth_bandlimited_997hz.wav --f0 997 --out results/nmr/sawtooth_bandlimited_997hz.nmr.json
```

The noise-to-mask ratio: each alias judged against the auditory masking
curve (simultaneous masking from the harmonics + the absolute threshold
of hearing), not a bare dB number. Pass is worst NMR <= 0 dB. The
band-limited sawtooth passes (no aliases); the naive one fails. On
Therum step 2's real wavetable render the 22 kHz alias is well masked
(NMR -69.80 dB) but the folded 48th harmonic at 143.6 Hz fails
(NMR +23.31 dB). See `docs/DSP_TEST_DESIGN.md`. Use `--ref-spl` to check
a different playback level (default 96 dB SPL = 0 dBFS).

## 8. Cramping test (Therum section 7 filter response)

```bash
python3 scripts/cramping_test.py data/test_tones/sweep_peaking_8000hz.wav --type peaking --fc 8000 --q 1.0 --gain-db 12 --out results/cramping/sweep_peaking_8000hz.cramping.json
```

Measures the filter's response from a log-sweep WAV against the analogue
prototype and reports the cramping error at the geometric-mean frequency
sqrt(fc * sr/2). The reference sweeps in `data/test_tones/sweep_*.wav`
were rendered through a built-in RBJ biquad; use
`--render-reference` to render your own. A standard RBJ biquad fails
the default 1 dB threshold (it is not decramped); a decramping method
should measure near 0 dB. See `docs/DSP_TEST_DESIGN.md`.

## 9. Make release evidence

```bash
python3 scripts/make_evidence_pack.py
```

## 10. Validate the whole repo

```bash
python3 scripts/validate_repo.py
```

## CLI wrapper

```bash
python3 scripts/arc_audiobench.py generate
python3 scripts/arc_audiobench.py batch data/test_tones --out results/batch
python3 scripts/arc_audiobench.py alias data/test_tones/sawtooth_bandlimited_997hz.wav --f0 997 --out results/alias/sawtooth_bandlimited_997hz.alias.json
python3 scripts/arc_audiobench.py nmr data/test_tones/sawtooth_bandlimited_997hz.wav --f0 997 --out results/nmr/sawtooth_bandlimited_997hz.nmr.json
python3 scripts/arc_audiobench.py cramping data/test_tones/sweep_peaking_8000hz.wav --type peaking --fc 8000 --q 1.0 --gain-db 12 --out results/cramping/sweep_peaking_8000hz.cramping.json
python3 scripts/arc_audiobench.py report results --out reports/index.html
python3 scripts/arc_audiobench.py evidence
```
