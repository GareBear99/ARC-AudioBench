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

## 9. STOI test (Vox8 intelligibility)

```bash
python3 scripts/stoi_test.py --generate-test data/test_tones/stoi_speech_like.wav
python3 scripts/stoi_test.py data/test_tones/stoi_speech_like.wav data/test_tones/stoi_speech_like_noisy0db.wav --out results/stoi/speech_like_vs_noisy0db.stoi.json
```

Objective intelligibility of a degraded speech signal vs a clean
reference (Taal et al. 2011). For Vox8: clean = dry modulator, degraded
= vocoded output. There is no speech corpus in the repo yet, so
`--generate-test` synthesises a speech-like signal for validation; a
real Vox8 measurement needs a real corpus and a FreeVox8 render. The
signals must be time-aligned and the same length. See
`docs/DSP_TEST_DESIGN.md`.

## 10. Freeze-blur test (Vox8 freeze pilot)

```bash
python3 scripts/freeze_blur_test.py --generate-test data/test_tones/freeze_vibrato_vowel.wav --f0 110
python3 scripts/freeze_blur_test.py data/test_tones/freeze_vibrato_vowel_frozen.wav --f0 110 --out results/freeze-blur/vowel_frozen.freeze.json
```

Measures the spectral blur of a frozen (or sustained) vibrato vowel:
peak-bin vs adjacent-bin energy per harmonic. No FreeVox8 render
exists yet, so `--generate-test` synthesises the validation set (static
vowel, vibrato vowel, simulated freeze); a real measurement needs a
FreeVox8 frozen vibrato render, with and without the WASPAA correction.
Use `--compare` for the corrected-vs-uncorrected comparison. See
`docs/DSP_TEST_DESIGN.md`.

## 11. Make release evidence

```bash
python3 scripts/make_evidence_pack.py
```

## 12. Validate the whole repo

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
python3 scripts/arc_audiobench.py stoi data/test_tones/stoi_speech_like.wav data/test_tones/stoi_speech_like_noisy0db.wav --out results/stoi/speech_like_vs_noisy0db.stoi.json
python3 scripts/arc_audiobench.py freeze-blur data/test_tones/freeze_vibrato_vowel_frozen.wav --f0 110 --out results/freeze-blur/vowel_frozen.freeze.json
python3 scripts/arc_audiobench.py report results --out reports/index.html
python3 scripts/arc_audiobench.py evidence
```
