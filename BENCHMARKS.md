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
