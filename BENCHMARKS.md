# ARC-AudioBench Benchmarks

## Signal benchmarks

| Signal | Purpose |
|---|---|
| `sine_100hz.wav` | low-frequency EQ and bass path sanity |
| `sine_1000hz.wav` | midrange unity/reference test |
| `sine_10000hz.wav` | high-frequency response sanity |
| `silence.wav` | noise/denormal/DC stability |
| `impulse.wav` | impulse response / latency / ringing observation |
| `log_sweep_20_20000hz.wav` | broad frequency response observation |
| `sawtooth_naive_997hz.wav` | alias-test negative control (must FAIL the alias test) |
| `sawtooth_bandlimited_997hz.wav` | alias-test positive control (must PASS the alias test) |

## Measured results

### WAV analysis (verified 2026-11-05, this repo, Python 3.12)

Regenerating the tones produces byte-identical files (all six original
tones reproduce exactly), and re-analysing `sine_1000hz.wav` reproduces the
committed 2026-05-06 result field-for-field: peak 0.4999694824, RMS
0.3535276408, crest 1.4142302459, DC 0.0, clipping 0, dominant frequency
1000.0 Hz, pass true. Batch: 6 of 6 analysed, 5 pass; `impulse.wav` is
CHECK by design (its full-scale single sample trips the clipping counter).

### Alias test (Therum section 7, measured 2026-11-05, 48 kHz)

| Signal | Harmonics | Aliases | ASR (dB) | Worst alias | Pass |
|---|---|---|---|---|---|
| Naive sawtooth 997 Hz | 24 | 2135 | -15.849 | -38.252 dBFS @ 22078 Hz | No |
| Band-limited sawtooth 997 Hz | 24 | 0 | -- | -- | Yes |

The worst alias (-38.252 dBFS at 22078.125 Hz) is the folded 26th
harmonic (48000 - 26*997 = 22078) at its theoretical level, which verifies
the FFT scaling. Full method, thresholds, and the NMR caveat (this is the
raw alias measurement, not a noise-to-mask ratio yet) are in
`docs/DSP_TEST_DESIGN.md`. Results live in `results/alias/`.

### NMR test (Therum section 7 acceptance test, measured 2026-11-05, 48 kHz, 997 Hz, ref 96 dB SPL)

| Signal | Worst NMR | Worst alias | 22 kHz alias NMR | Pass |
|---|---|---|---|---|
| Therum mipped wavetable (step 2 render) | +23.31 dB @ 143.6 Hz | -55.51 dBFS | -69.80 dB | No |
| Therum naive wavetable (control) | +42.04 dB @ 287.1 Hz | -44.11 dBFS | -- | No |
| Naive sawtooth 997 Hz | +36.05 dB @ 287.1 Hz | -50.10 dBFS | -62.25 dB | No |
| Band-limited sawtooth 997 Hz | -- (no aliases) | -- | -- | Yes |

The 22 kHz alias the alias test flags as worst is well masked (NMR
-69.80 dB on the Therum mipped render) -- it is inaudible. The aliases
that fail the test are the low-frequency folded harmonics: the folded
48th harmonic at 143.6 Hz (-55.51 dBFS, expected fold 48000 - 48*997 =
144 Hz) sits 23.31 dB above the masking curve. The mipped engine is
12.7-18.7 dB better than naive on worst NMR, but it still fails the
criterion. Full method and the level-dependence note (the low-frequency
NMR is set by the absolute threshold, so it depends on playback level)
are in `docs/DSP_TEST_DESIGN.md`. Results live in `results/nmr/`.

### Cramping test (Therum section 7 filter response, measured 2026-11-05, 48 kHz, reference RBJ renders)

| Filter | f_geo | Analytical error | Sweep-measured error | Agreement |
|---|---|---|---|---|
| Peaking, fc 8000, +12 dB, Q 1.0 | 13856 Hz | -2.010 dB | -2.026 dB | 0.016 dB |
| Lowpass, fc 8000, Q 0.707 | 13856 Hz | -3.983 dB | -4.201 dB | 0.218 dB |
| Highpass, fc 8000, Q 0.707 | 13856 Hz | +0.281 dB | +0.271 dB | 0.010 dB |

The sweep measurement matches the analytical error (from the z-transform
of the coefficients vs the analogue prototype) for the same filter, so
the test measures the cramping error correctly. The lowpass agreement is
looser because its rolloff is steep within a 1/12-octave bin. The
FreeEQ8 baseline (-3.383 dB at 18783 Hz) is their filter configuration's
error; the error magnitude depends on fc, gain, Q, and sample rate.
Full method and the peaking-at-fc bin-averaging note are in
`docs/DSP_TEST_DESIGN.md`. Results live in `results/cramping/`; reference
sweeps in `data/test_tones/sweep_*.wav`.

## Plugin benchmarks

- pluginval strictness 10 result
- DAW load/scan report
- preset recall report
- automation write/read report
- sample-rate transition report
- buffer-size transition report
- rendered WAV analysis before/after processing

## Evidence outputs

- analysis JSON
- comparison JSON
- HTML report
- Markdown summary
- release manifest
- source inventory
