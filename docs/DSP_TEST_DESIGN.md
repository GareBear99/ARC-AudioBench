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

**What this is NOT.** Therum section 7 specifies the alias test as
a noise-to-mask ratio (NMR): aliases below the auditory masking curve, not
a bare dB number. This script measures the alias energy and the worst alias
level -- the raw quantities an NMR is computed from. The NMR itself is
`scripts/nmr_test.py` (see below). The pass
thresholds (worst alias -60 dBFS, ASR -40 dB) are provisional bench values,
not literature values. Do not cite these numbers as an NMR.

## NMR test (`scripts/nmr_test.py`) -- Therum section 7, the acceptance test

The V\xc3\xa4lim\xc3\xa4ki school's criterion (V\xc3\xa4lim\xc3\xa4ki & Huovilainen 2007;
V\xc3\xa4lim\xc3\xa4ki, Nam, Smith & Abel 2010; Kahles, Esqueda & V\xc3\xa4lim\xc3\xa4ki 2019):
aliases are judged against the auditory masking curve, not a bare dB
number. Same window and FFT as the alias test, same peak classification
(harmonics = tonal maskers, the rest = aliases). The masking threshold is
built from the harmonics with the Zwicker Bark scale, the Schroeder
spreading function (MPEG-1 Psychoacoustic Model 1), and the Terhardt
absolute threshold of hearing (0 dBFS taken as 96 dB SPL by default,
configurable with `--ref-spl`). For each alias, NMR = alias level -
masking threshold, in dB. Two NMRs are reported: total (simultaneous
masking + ATH -- the audibility verdict) and simultaneous-only (harmonics
alone, ignoring the ATH -- the informative number when the ATH dominates,
e.g. an alias above 20 kHz). Pass: worst NMR <= 0 dB, every alias below
the masking curve.

**Measured results (2026-11-05, 48 kHz, 997 Hz, ref 96 dB SPL):**

| Signal | Worst NMR | Worst alias | 22 kHz alias NMR | Pass |
|---|---|---|---|---|
| Therum mipped wavetable (step 2 render) | +23.31 dB @ 143.6 Hz | -55.51 dBFS | -69.80 dB | No |
| Therum naive wavetable (control) | +42.04 dB @ 287.1 Hz | -44.11 dBFS | -- | No |
| Naive sawtooth (Bench tone) | +36.05 dB @ 287.1 Hz | -50.10 dBFS | -62.25 dB | No |
| Band-limited sawtooth (Bench tone) | -- (no aliases) | -- | -- | Yes |

**What the NMR found that the bare dB number missed.** The 22 kHz alias
the alias test flags as worst (-45.80 dBFS at 22078 Hz on the Therum
mipped render) is well masked: NMR -69.80 dB total, -23.86 dB
simultaneous-only. It is inaudible. The aliases that actually fail the
test are the low-frequency folded harmonics: the folded 48th harmonic at
143.6 Hz (-55.51 dBFS, verified against the expected fold 48000 - 48*997
= 144 Hz) sits 23.31 dB above the masking curve, because at 144 Hz the
absolute threshold is only ~17 dB SPL and the harmonics (starting at 997
Hz, ~7 Bark away) provide almost no simultaneous masking. The folded
47th harmonic at 1139.7 Hz (-56.62 dBFS, expected fold 1141 Hz) is the
same story. The mipped engine is 12.7-18.7 dB better than naive on worst
NMR, but it still fails the criterion: the top mip level's surviving
harmonics fold back to low frequencies where they are audible at a loud
listening level. Note the level dependence: the low-frequency NMR is set
by the absolute threshold, so at a quieter playback level (lower
--ref-spl) the same aliases measure lower; re-run with --ref-spl to
check a different listening level. Results live in `results/nmr/`.

**What the NMR is NOT.** It is not the full MPEG-1 Psychoacoustic Model
1: there is no tonality estimation (the harmonics are tonal maskers by
construction, correct for a periodic oscillator), no 0.5-Bark grouping,
and no temporal masking. It is not an ABX listening test: the NMR
predicts audibility from the masking model, and the paper's ABX protocol
is the listening confirmation.

## Cramping test (`scripts/cramping_test.py`) -- Therum section 7, filter response

The FreeEQ8 baseline: a standard digital biquad (RBJ, bilinear transform)
loses -3.383 dB against its analogue prototype at the geometric-mean
frequency, sqrt(fc * sr/2). The SVF does not decramp. This test measures
that error for any filter render, so Therum step 3's decramping
hypothesis (geometric-mean 5th constraint vs Orfanidis vs
Sarkka-Huovilainen) can be tested on the same rig.

Method: a log sine sweep (20 Hz to 20 kHz, 8 s in the reference render)
through the filter, covering the whole WAV from t=0. The sweep is split
into 1/12-octave bins; the RMS in each bin gives the digital magnitude at
the bin's geometric-centre frequency (a sine's RMS is amplitude/sqrt(2)).
The analogue prototype magnitude at the same frequency comes from the
standard analogue transfer function (peaking / 2nd-order lowpass /
2nd-order highpass -- the prototypes RBJ's coefficients are the bilinear
transform of). Error = digital - analogue, in dB. The headline number is
the error at the geometric-mean frequency f_geo = sqrt(fc * sr/2). An
unfiltered sweep WAV can be passed as --reference to measure the input
level per bin instead of assuming the input amplitude. Pass: --max-error-db
(default 1.0 dB) at f_geo. A standard RBJ biquad fails this threshold --
correctly, it is not decramped. A decramping method should measure near
0 dB and pass.

**Reference render.** `--render-reference` renders the same sweep through
a built-in Python RBJ biquad and writes the WAV, and prints the analytical
error at f_geo (from the z-transform of the coefficients vs the analogue
prototype) for comparison with the sweep measurement. This is how the
test is validated.

**Measured results (2026-11-05, 48 kHz, reference renders):**

| Filter | f_geo | Analytical error | Sweep-measured error | Agreement |
|---|---|---|---|---|
| Peaking, fc 8000, +12 dB, Q 1.0 | 13856 Hz | -2.010 dB | -2.026 dB | 0.016 dB |
| Lowpass, fc 8000, Q 0.707 | 13856 Hz | -3.983 dB | -4.201 dB | 0.218 dB |
| Highpass, fc 8000, Q 0.707 | 13856 Hz | +0.281 dB | +0.271 dB | 0.010 dB |

The lowpass agreement is looser because its rolloff is steep: the
magnitude changes appreciably across one 1/12-octave bin, so the bin RMS
is an average over the bin rather than the centre value. The peaking
reference with --reference (unfiltered sweep, gain 0 dB) measures exactly
the same -2.026 dB as without it, so the reference path is verified. The error at fc itself is a check on the rig, not on the filter: the
bilinear transform with pre-warping matches the analogue exactly at fc,
so the analytical error there is 0 dB for all three types (verified:
peaking 12.000 dB digital vs 12.000 dB analogue; lowpass -3.012 dB vs
-3.012 dB). The sweep-measured error at fc is ~0 dB for lowpass/highpass
(0.022 dB, -0.024 dB) but -4.011 dB for peaking. That is a measurement
artifact, not cramping: fc is the peak of the peaking response, so the
bin RMS averages over the peak's curvature and reads below the peak
value. For lowpass/highpass, fc is on a locally-linear slope, so the bin
average is the centre value. It does not affect the headline metric (the
error at f_geo), because at f_geo the response is on a slope: the
peaking agreement there is 0.016 dB. The -3.383 dB FreeEQ8 baseline is
their filter configuration's error at their geometric mean (18783 Hz);
the error magnitude depends on fc, gain, Q, and sample rate, so
different configurations measure different numbers. What the test
validates is the measurement: the sweep number matches the analytical
number for the same filter. Results live in `results/cramping/`;
reference sweeps in `data/test_tones/sweep_*.wav`.

## STOI test (`scripts/stoi_test.py`) -- Vox8 intelligibility

Taal et al. 2011: the objective intelligibility of a degraded speech
signal against a clean reference. For Vox8 the clean reference is the
dry modulator (spoken vocal) and the degraded signal is the vocoded
output; the fixed corpus is 10 Harvard/IEEE sentences, one male and one
female speaker. This script reports the scalar STOI and all 15
one-third-octave band scores.

Method (the published algorithm, clean-room implementation, stdlib
only): resample both signals to 10 kHz (windowed-sinc FIR lowpass +
linear interpolation); STFT, Hann window 256 samples, hop 128; group
the magnitude spectrum into 15 one-third-octave bands (centre
frequencies 150 Hz to ~3.8 kHz, band edges at the geometric means of
adjacent centres, band value = sum of magnitudes in the band); remove
silent frames (clean frame energy more than 40 dB below the maximum);
split into short-time segments of 30 frames (384 ms); in each segment
and band, normalise the degraded envelope to the clean envelope's
energy, clip it from below at -15 dB relative to the clean envelope,
and take the Pearson correlation. STOI is the mean correlation over all
bands and segments, in [0, 1].

**What it is not.** It is not the reference MATLAB code: the resampler
is a windowed-sinc FIR + linear interpolation (not a polyphase filter),
and the band grouping sums magnitudes (not powers). It is not a
listening test: STOI predicts intelligibility from the signal, and the
Vox8 listening protocol is the confirmation. It does not measure
quality, musicality, or the top octave: STOI is defined at 10 kHz, so
it says nothing above 5 kHz, where Air lives. And it needs time
alignment: a misaligned degraded signal scores lower for alignment, not
for intelligibility -- compensate the Ghost frame delay (~23 ms at
44.1 kHz) before running it.

**Speech corpus: there is none in this repo.** The test signal
generator (`--generate-test`) synthesises a speech-like signal (vowel
formants, pitch contour, syllabic amplitude) so the implementation can
be validated without a corpus. STOI numbers on the synthetic signal are
for relative comparison and for validating the implementation -- they
are NOT a claim about Vox8's intelligibility on real speech. A real
Vox8 measurement needs a real speech corpus and a FreeVox8 render.

**Measured results (2026-11-05, synthetic speech-like signal, 3 s, 10 kHz):**

| Degradation | STOI |
|---|---|
| Identity (clean vs clean) | 1.000 |
| Silence (clean vs silence) | 0.000 |
| Gain x0.5 / x2.0 (pure gain change) | 1.000 / 1.000 |
| Time shift 12.8 ms (one frame) | 0.860 |
| White noise, SNR +10 dB | 0.511 |
| White noise, SNR +5 dB | 0.416 |
| White noise, SNR 0 dB | 0.315 |
| White noise, SNR -5 dB | 0.217 |
| Vocoder-like (noise shaped by the envelope) | 0.481 |

Identity = 1.0 exactly, silence = 0, gain invariance holds, and STOI
is monotone in SNR -- the implementation behaves as STOI should. The
absolute numbers are for the synthetic signal only; on real speech the
same degradations score differently. Note on sample rate: STOI is
defined at 10 kHz, so noise above 5 kHz does not count. A 48 kHz render
with white noise at 0 dB SNR scores 0.489, not 0.315, because the
resampler's anti-alias filter removes the out-of-band noise and the
in-band SNR is effectively ~+7 dB. When comparing SNRs across sample
rates, compare the in-band SNR. Results live in `results/stoi/`; the
test signal is `data/test_tones/stoi_speech_like.wav`.

## What is not implemented yet

See `docs/MEASUREMENT_PLAN.md` for the full Therum section 7 + Vox8
measurement plan mapped to Bench status: filter response / cramping test,
CPU benchmarks + instance scaling, latency, real-time safety, STOI, and
the freeze-blur test. Those need a built plugin (and, for CPU/latency, a
host) -- the Bench analyses rendered WAVs; it does not host plugins.
