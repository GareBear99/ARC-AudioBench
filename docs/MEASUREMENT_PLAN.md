# Measurement Plan — Therum section 7 + Vox8, mapped to ARC-AudioBench

Source of the plan: Therum paper section 7 ("A claim in this paper is not
a result until the test in this section produces a number") and the Vox8
measurement report (`vox8-measurement-vocoder-state-of-art-research.md`).
The FreeEQ8 paper is the method reference: its filter-response rig (sweep
a sine 20 Hz-20 kHz, measure RMS magnitude ratio against the analogue
prototype), its cramping analysis (-3.383 dB at the geometric-mean
frequency, identical for RBJ and SVF -- SVF does not decramp), its CPU
method (median of 16 trials, warmup discarded), its instance scaling
(1 to 128), and its SPSC result (0 tears across 239M samples) are the
baselines this bench measures against. Use the FreeEQ8 paper's PROVEN
findings (the measured results, the cramping analysis, the filter work),
not its over-claims: variable-cadence Dynamic EQ exists only in test
simulators, Natural Phase is dead code, Smart EQ has zero production
callers, and the headline CPU percentages are doubled (0.62% is really
0.31%). Those gaps are being filled in FreeEQ8; the bench re-measures when
they land.

## Status key

- **Implemented** -- a script in `scripts/` does this, with a verified test.
- **Protocol** -- the procedure is specified here; running it needs a built
  plugin and/or a host, which the bench does not provide.
- **Not started** -- specified in the source paper/report, not yet in the
  bench in any form.

## Therum section 7 tests

| Test | Status | Notes |
|---|---|---|
| Alias test (headline) | **Implemented** (`scripts/alias_test.py` + `scripts/nmr_test.py`) | FFT alias energy + worst alias level, and the NMR masking-curve model that judges them (Therum section 7's actual criterion). Validated on the naive vs band-limited 997 Hz sawtooth pair (see `docs/DSP_TEST_DESIGN.md`) and on Therum step 2's real wavetable render: mipped ASR -33.23 dB / worst alias -45.80 dBFS, worst NMR +23.31 dB at 143.6 Hz (the folded 48th harmonic) -- the 22 kHz alias is well masked (NMR -69.80 dB), the low-frequency folded harmonics are the ones that fail. |
| Filter response test | **Implemented** (`scripts/cramping_test.py`) | Log sine sweep (20 Hz-20 kHz) through the filter, RMS magnitude per 1/12-octave bin vs the analogue prototype, error at the geometric-mean frequency sqrt(fc * sr/2). Baseline to beat: -3.383 dB (FreeEQ8, their filter configuration). Validated on the built-in RBJ reference renders: the sweep measurement matches the analytical error (from the z-transform of the coefficients) to 0.016 dB (peaking, fc 8000, +12 dB, Q 1.0: measured -2.026 dB vs analytical -2.010 dB at 13856 Hz), 0.218 dB (lowpass, fc 8000, Q 0.707: -4.201 vs -3.983 dB -- the steeper rolloff smears a bin), and 0.010 dB (highpass: +0.271 vs +0.281 dB). The decramping hypothesis (geometric-mean 5th constraint vs Orfanidis vs Sarkka-Huovilainen) is tested on this rig -- Therum step 3's reference. |
| CPU benchmarks | **Protocol** | ns/sample and cycles/sample per voice / filter / oversampling factor, on the target hardware. Instance scaling 1 to 128 (FreeEQ8 method) -- per-instance cost rise + total CPU at 128. No CPU figure from the literature is quoted as a Therum result. Needs a built plugin + host; the bench cannot measure plugin CPU from a WAV. Reference hardware: the 2018 Intel Mac mini. |
| Latency | **Protocol** | Samples + ms per mode (base, each oversampling factor, convolution partition, linear-phase). Host delay compensation honoured. Needs a built plugin + host. |
| Real-time safety | **Protocol** | Zero allocations on the audio thread (test counts allocations during processBlock, not by inspection). SPSC stress: 400 ms trials, samples produced / buffers consumed / data tears -- FreeEQ8 result to match is 0 tears across 239M samples. Denormal handling (ScopedNoDenormals-equivalent), verified by a denormal-input test. Needs the plugin's own test harness; the bench records the result. |
| Perceptual tests (ABX) | **Protocol** | ABX using the FreeEQ8 ABX infrastructure (40 randomised trials per participant, binomial test, d-prime, Wilson 95% CI). The FreeEQ8 pilot (N=1, 55% hit rate, p=0.635, d-prime 0.25) is the standard for reporting a null result honestly. A formal study (N>=20, power >0.85 for d-prime >=0.5) is planned before any perceptual claim is published. Listening tests are run by people, not by this repo. |
| Plugin validation | **Implemented (wrapper)** (`scripts/pluginval_wrapper.py`) | pluginval strictness 10 on VST3/AU/CLAP, buffer sizes 32-8192, sample rates 22050-192000 Hz, rapid automation, thread safety. Records the command; runs pluginval only when the binary + plugin path are provided (`--run`). AU via auval, CLAP via the CLAP validator. Failures block release. |
| Preset / state round-trip | **Protocol** | Save -> load -> bit-identical parameters, including wavetables and mod-matrix routings. Parameter indices frozen before the first release. Needs a built plugin + host. |

## Vox8 tests (from the Vox8 measurement report)

| Test | Status | Notes |
|---|---|---|
| STOI intelligibility | **Not started** | Taal et al. 2011. Clean reference = dry modulator (spoken vocal); degraded = vocoded output; fixed corpus (10 Harvard/IEEE sentences, one male + one female speaker); fixed carrier; report all 15 one-third-octave band scores, not just the scalar. Needs a speech corpus + the STOI algorithm + a FreeVox8 render. The algorithm is specified in the report (10 kHz resample, 256-sample Hann 50% overlap, 384 ms segments, 40 dB silence rule). Limits: STOI predicts intelligibility of speech, not quality of singing or of a robot-voice effect; it needs time alignment (the Ghost frame delay must be compensated first); its 10 kHz cap says nothing about the top octave, where Air lives. |
| Artefact taxonomy (listening checklist) | **Protocol** | Phasiness, transient smearing/doubling, musical noise, consonant loss, freeze blur/wobble, formant-shift artefacts, pumping. Each artefact has a named test in the Vox8 report. Listening tests are run by people. |
| Freeze-blur test | **Not started** | Vox8's equivalent of the alias test: sustained vibrato vowel (5-7 Hz, +/-0.5 semitone) frozen; peak-bin vs adjacent-bin energy, with/without the WASPAA 2001 correction. The pilot is designed (Vox8 ghost/morph report section 2.3); it has not been run. Needs a FreeVox8 render. FreeVox8's Ghost 1024 backend (`Source/DSP/FreeVox8SpectralEngine.h`, kFftSize 1024, kDisplayBins 128) is the code under test; `analyseBins()` is the cost driver (~11M transcendental calls/sec/channel at 44.1 kHz, computed from the code). |
| Latency / CPU (vocoder) | **Protocol** | Per engine (Low Latency 128 filterbank, Ghost 1024 STFT/OLA), at 44.1 / 48 / 96 kHz, buffers 1 / 16 / 32 / 64 / 128 / 512 / 1024 / 2048, with silence / spoken vocal / drum modulator in, 1 and N instances, mean + worst-case block time. Market anchor: Waves Morphoder, 639 samples latency at 44.1-48 kHz (verified from Waves' spec table). Ghost frame delay ~23 ms at 44.1 kHz is an estimate from the code structure (1024-sample window), to be measured, not asserted. Reference hardware: the 2018 Intel Mac mini. |
| Competitor A/B | **Protocol** | Same corpus + carrier against TAL-Vocoder (free, 11 bands), Ableton Live Vocoder (stock), iZotope VocalSynth 2 (premium bar, released May 2018, still current). Do NOT benchmark against singing synths (Vocaloid / Synthesizer V / UTAU are a different product category). |
| FreeVox8 golden tests | **Implemented (gate, in the FreeVox8 repo)** | `docs/DSP_GOLDEN_TESTS.md` in `GareBear99/FreeVox8`: silence in, no NaN/Inf at parameter extremes, freeze toggling clicks, host bypass bit-stable, MIDI note changes, sidechain layouts, sample rates 44.1-192 kHz, buffers 1-2048, pluginval strictness 10; musical acceptance (intelligible at 128 bands, Mask pocket, Ghost character, Morph bounded). The golden tests are the gate; this bench is the benchmark. Both are needed. |

## What the bench needs from the plugins

Therum and Vox8 are the test drivers: they are what the bench measures.
The bench is built by testing it against them. Current state (2026-11-05):

- **FreeEQ8 is the working test subject.** The free build is genuinely
  good (RBJ path correct, pluginval strictness 10 passes). The bench's
  FreeEQ8 suite (`docs/FREEEQ8_BENCHMARK_SUITE.md`: bypass null render,
  LP/HP sweep, bell boost/cut at 100 Hz / 1 kHz / 10 kHz, M/S routing,
  preset recall, automation ramp, analyzer/UI stress, pluginval 10) runs
  against its renders once they exist.
- **Therum is not built yet.** The repo (`GareBear99/Therum_JUCE-Plugin`)
  is a scaffold (sine-only wavetable, no real FX, never compiled as a
  plugin). The Therum build is now background/gap work (Gary, 2026-11-05):
  the paper's 14-step build order, in iPlug2, in small steps. The bench's
  alias test, filter response test, and CPU benchmarks become runnable
  against the real wavetable oscillator once the build produces a plugin.
  Until then the bench validates against synthetic signals (the naive vs
  band-limited sawtooth pair).
- **FreeVox8 is not built here.** The repo (`GareBear99/FreeVox8`,
  HEAD 02eedfe) is a JUCE spectral vocoder v0.5.0 with its own paper and
  golden tests. The bench's STOI, freeze-blur, and vocoder CPU/latency
  tests need a FreeVox8 render. Vox8 is iPlug2 going forward (Gary,
  2026-11-05: iPlug2 until our own language out of ARC Audio Bench), so
  the Vox8 build is a fresh build or a port, not a finish of the JUCE repo
  as-is -- that call is still open.
