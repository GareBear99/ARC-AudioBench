# DSP Test Design

Baseline signals are intentionally simple: silence, sine, sweep, impulse.
Simple signals make regressions easier to detect. Complex music tests can
be added later after the baseline passes.

## Test tones (`scripts/generate_test_tones.py`)

All tones are deterministic (regenerating them produces byte-identical
files -- verified 2026-11-05: all six original tones reproduce exactly).
48 kHz, 2.0 s, 16-bit mono, amplitude 0.5 unless noted.

| Tone | Purpose |
|---|---|
| `sine_100hz.wav` | Low-frequency EQ and bass path sanity |
| `sine_1000hz.wav` | Midrange unity / reference test |
| `sine_10000hz.wav` | High-frequency response sanity |
| `silence.wav` | Noise / denormal / DC stability |
| `impulse.wav` | Impulse response / latency / ringing observation (full-scale single sample -- trips the clipping counter by design, so its `pass` is false; that is expected, not a failure) |
| `log_sweep_20_20000hz.wav` | Broad frequency response observation |
| `sawtooth_naive_997hz.wav` | Alias-test negative control: a naive phase-ramp sawtooth. Must FAIL the alias test. |
| `sawtooth_bandlimited_997hz.wav` | Alias-test positive control: additive sawtooth, harmonics to Nyquist only, normalised to peak 0.5. Must PASS the alias test. |

## Alias test (`scripts/alias_test.py`) -- Therum section 7, headline test

Given a rendered WAV of a periodic oscillator at a known fundamental f0,
measure the alias products: spectral energy that is NOT at an integer
multiple of f0.

Method: skip the first 0.5 s (onset), take a 16384-sample Hann window,
radix-2 FFT (pure Python, stdlib only), find peaks above a -80 dBFS floor,
classify each peak as harmonic (within 2 FFT bins of k*f0) or alias, and
report:

- **alias_to_signal_ratio_db** -- alias peak energy / harmonic peak energy.
  Computed from detected peaks, so it includes some windowing leakage and
  is a conservative (upper-bound) estimate of alias energy.
- **worst_alias_dbfs / worst_alias_hz** -- the strongest single alias
  component. This is the precise metric: on the naive 997 Hz sawtooth it
  reads -38.252 dBFS at 22078.125 Hz, which is the folded 26th harmonic
  (48000 - 26*997 = 22078) at its theoretical level (20*log10 of
  (2/pi)*0.5/26 = -38.24 dBFS). The FFT scaling is verified by that match.
- **alias_peak_count** -- informational only; it counts leakage sidelobes
  as well as true aliases, so it is not the decision metric.

**Why 997 Hz.** If f0 divides the sample rate evenly (e.g. 1000 Hz at
48 kHz), every folded alias lands exactly on a harmonic bin and is
invisible to this test. 997 Hz does not divide 48000, so folded aliases
land at non-harmonic frequencies and are detectable.

**Measured results (2026-11-05, this repo, 48 kHz):**

| Signal | Harmonics | Aliases | ASR (dB) | Worst alias | Pass |
|---|---|---|---|---|---|
| Naive sawtooth 997 Hz | 24 | 2135 | -15.849 | -38.252 dBFS @ 22078 Hz | No |
| Band-limited sawtooth 997 Hz | 24 | 0 | -- | -- | Yes |

**What this is NOT (yet).** Therum section 7 specifies the alias test as
a noise-to-mask ratio (NMR): aliases below the auditory masking curve, not
a bare dB number. This script measures the alias energy and the worst alias
level -- the raw quantities an NMR is computed from. A masking-curve model
(the NMR itself) is the next step and is NOT implemented here. The pass
thresholds (worst alias -60 dBFS, ASR -40 dB) are provisional bench values,
not literature values. Do not cite these numbers as an NMR.

## What is not implemented yet

See `docs/MEASUREMENT_PLAN.md` for the full Therum section 7 + Vox8
measurement plan mapped to Bench status: filter response / cramping test,
CPU benchmarks + instance scaling, latency, real-time safety, STOI, and
the freeze-blur test. Those need a built plugin (and, for CPU/latency, a
host) -- the Bench analyses rendered WAVs; it does not host plugins.
