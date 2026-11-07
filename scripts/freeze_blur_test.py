#!/usr/bin/env python3
"""Freeze-blur test for ARC-AudioBench.

The Vox8 freeze pilot: a sustained vibrato vowel (5-7 Hz, +/-0.5
semitone) is frozen (one STFT frame held and repeated). The freeze
blurs the spectrum: the STFT window smears each harmonic across
adjacent bins, and the vibrato smears it further while the pitch moves
inside the analysis window. The WASPAA 2001 beta/lambda correction is
supposed to sharpen the frozen spectrum. This test measures the blur
so the correction can be judged.

Method: given a WAV of a frozen (or sustained) vowel and its fundamental
f0, compute the average magnitude spectrum (Hann window, configurable
FFT size, default 4096 for fine resolution) and, for each harmonic,
measure the peak-bin magnitude against the adjacent bins:
    blur_db = 20*log10(mean(|X[k-1]|, |X[k+1]|) / |X[k]|)
A sharp peak has a very negative blur (adjacent bins far below the
peak); a blurred peak has a blur closer to 0 dB. The headline numbers
are the magnitude-weighted mean blur over the harmonics and the worst
(least negative) single-harmonic blur. --compare runs the same
measurement on two WAVs (e.g. corrected vs uncorrected freeze) and
reports the difference -- the correction gain.

The pilot's decision rule is written in advance in the Vox8 paper
section 4: if the correction does not reduce the blur enough, the
freeze blur stays a known bounded limitation. This script is the
measurement; the decision is the paper's.

No Vox8 render exists yet, so the validation is on synthetic signals
(--generate-test): a static vowel (the blur floor, window smearing
only), a vibrato vowel (higher blur, the pitch moves inside the window),
and a simulated freeze of the vibrato vowel (one STFT frame held and
overlap-added). The harness must distinguish the static vowel (low
blur) from the frozen vibrato (higher blur). A real measurement needs
a FreeVox8 frozen vibrato render, with and without the WASPAA
correction.

Usage:
    python3 scripts/freeze_blur_test.py frozen.wav --f0 110 --out results/freeze-blur/frozen.freeze.json
    python3 scripts/freeze_blur_test.py frozen.wav --f0 110 --compare uncorrected.wav --out results/freeze-blur/compare.freeze.json
    python3 scripts/freeze_blur_test.py --generate-test data/test_tones/freeze_test.wav
"""

import argparse
import json
import math
import struct
import sys
import wave
from pathlib import Path

SCHEMA_VERSION = "arc-audiobench-freeze-blur-v1"

DEFAULT_FFT_SIZE = 4096   # analysis FFT (finer than Ghost's 1024; this is
                          # the measurement instrument, not the code under test)
DEFAULT_F0 = 110.0        # Hz, sustained vowel fundamental
VIBRATO_RATE = 6.0        # Hz, the pilot's 5-7 Hz
VIBRATO_DEPTH = 0.5       # semitones, the pilot's +/-0.5
GHOST_FFT_SIZE = 1024     # FreeVox8 Ghost backend frame size (for the
                          # simulated freeze)
GHOST_HOP = 256

# Average adult-male vowel formants (F1, F2, F3 in Hz). Textbook values,
# used only to synthesise the test vowel.
VOWEL_A = (730.0, 1090.0, 2440.0)


# ---------------------------------------------------------------- WAV I/O

def read_wav(path):
    """Read a WAV file. Returns (samples, sample_rate); samples are floats
    in [-1, 1]. Accepts 16/24/32-bit integer mono (stereo: left channel)."""
    with wave.open(str(path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
    if sampwidth == 2:
        fmt = "<%dh" % (len(raw) // 2)
        ints = struct.unpack(fmt, raw)
        scale = 32768.0
    elif sampwidth == 3:
        ints = []
        for i in range(0, len(raw) - 2, 3):
            v = raw[i] | (raw[i + 1] << 8) | (raw[i + 2] << 16)
            if v >= 1 << 23:
                v -= 1 << 24
            ints.append(v)
        scale = 8388608.0
    elif sampwidth == 4:
        fmt = "<%di" % (len(raw) // 4)
        ints = struct.unpack(fmt, raw)
        scale = 2147483648.0
    else:
        raise ValueError("unsupported sample width: %d bytes" % sampwidth)
    if n_channels == 1:
        samples = [v / scale for v in ints]
    else:
        samples = [ints[i] / scale for i in range(0, len(ints), n_channels)]
    return samples, sample_rate


def write_wav(path, samples, sample_rate):
    """Write mono float samples in [-1, 1] as a 16-bit WAV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = b"".join(
        struct.pack("<h", max(-32768, min(32767, int(round(s * 32767.0)))))
        for s in samples
    )
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


# ------------------------------------------------------------------- FFT

def _fft(x):
    """Iterative radix-2 Cooley-Tukey FFT. x is a list of complex, len power of 2."""
    n = len(x)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            x[i], x[j] = x[j], x[i]
    length = 2
    while length <= n:
        ang = -2.0 * math.pi / length
        wlen = complex(math.cos(ang), math.sin(ang))
        half = length // 2
        for i in range(0, n, length):
            w = 1 + 0j
            for k in range(half):
                u = x[i + k]
                v = x[i + k + half] * w
                x[i + k] = u + v
                x[i + k + half] = u - v
                w *= wlen
        length *= 2
    return x


def _hann(n):
    return [0.5 * (1.0 - math.cos(2.0 * math.pi * i / (n - 1))) for i in range(n)]


def _average_magnitude_spectrum(x, fft_size):
    """Mean magnitude spectrum over Hann-windowed frames (hop = fft_size/4).
    Returns a list of magnitudes for bins 0..fft_size/2."""
    window = _hann(fft_size)
    hop = fft_size // 4
    acc = [0.0] * (fft_size // 2 + 1)
    n_frames = 0
    for start in range(0, len(x) - fft_size + 1, hop):
        seg = [x[start + i] * window[i] for i in range(fft_size)]
        spec = _fft([complex(v, 0.0) for v in seg])
        for k in range(fft_size // 2 + 1):
            acc[k] += abs(spec[k])
        n_frames += 1
    if n_frames == 0:
        raise ValueError("signal too short for a %d-sample FFT frame"
                         % fft_size)
    return [v / n_frames for v in acc]


# ------------------------------------------------------------- blur measure

def analyze_freeze_blur(wav_path, f0, fft_size=DEFAULT_FFT_SIZE,
                        mag_threshold_db=-60.0, max_blur_db=None):
    """Measure the freeze blur of a sustained-vowel WAV.

    Returns a dict with the per-harmonic blur and the summary numbers.
    Harmonics whose peak magnitude is more than mag_threshold_db below
    the strongest harmonic are dropped: they sit at the quantisation /
    numerical floor and their blur is meaningless.

    ``max_blur_db`` is an optional pass threshold on the mean blur
    (more negative = sharper): when given, the result carries ``pass``
    (mean blur <= threshold); when omitted the result reports the
    value only and ``pass`` is None.
    """
    x, sr = read_wav(wav_path)
    if fft_size > len(x):
        raise ValueError("signal (%d samples) shorter than the FFT size %d"
                         % (len(x), fft_size))
    if f0 <= 0.0 or f0 >= sr / 2.0:
        raise ValueError("f0 %.1f Hz is outside (0, %.0f)" % (f0, sr / 2.0))
    mag = _average_magnitude_spectrum(x, fft_size)
    bin_hz = sr / fft_size
    n_harmonics = int((sr / 2.0) // f0)
    harmonics = []
    for h in range(1, n_harmonics + 1):
        f_h = h * f0
        k = int(round(f_h / bin_hz))
        if k < 1 or k >= len(mag) - 1:
            continue
        # Peak bin: the max within +/-1 bin of the expected bin (the
        # harmonic need not sit exactly on a bin centre).
        k_peak = max((k - 1, k, k + 1), key=lambda kk: mag[kk])
        if k_peak < 1 or k_peak >= len(mag) - 1:
            continue
        peak = mag[k_peak]
        if peak <= 0.0:
            continue
        adj = 0.5 * (mag[k_peak - 1] + mag[k_peak + 1])
        blur_db = 20.0 * math.log10(adj / peak) if adj > 0.0 else float("-inf")
        harmonics.append({
            "harmonic": h,
            "frequency_hz": round(f_h, 1),
            "peak_bin": k_peak,
            "peak_mag": round(peak, 6),
            "adjacent_mag": round(adj, 6),
            "blur_db": round(blur_db, 3) if blur_db != float("-inf") else None,
        })
    if not harmonics:
        raise ValueError("no harmonics found (f0 %.1f Hz, %d Hz, FFT %d)"
                         % (f0, sr, fft_size))
    # Drop harmonics at the floor: peak more than mag_threshold_db below
    # the strongest harmonic.
    max_peak = max(h["peak_mag"] for h in harmonics)
    floor = max_peak * 10.0 ** (mag_threshold_db / 20.0)
    harmonics = [h for h in harmonics if h["peak_mag"] >= floor]
    if not harmonics:
        raise ValueError("no harmonics above the %.0f dB magnitude floor"
                         % mag_threshold_db)
    # Magnitude-weighted mean blur (the loud harmonics dominate the
    # percept) and the worst (least negative) single-harmonic blur.
    weights = [h["peak_mag"] for h in harmonics]
    blurs = [h["blur_db"] for h in harmonics if h["blur_db"] is not None]
    if not blurs:
        raise ValueError("no measurable adjacent-bin energy")
    wsum = sum(weights)
    mean_blur = (sum(w * b for w, b in zip(weights, blurs)) / wsum
                 if wsum > 0 else sum(blurs) / len(blurs))
    result = {
        "schema_version": SCHEMA_VERSION,
        "tool": "ARC-AudioBench",
        "analysis_type": "freeze_blur_test",
        "input": str(wav_path),
        "f0_hz": f0,
        "fft_size": fft_size,
        "sample_rate_hz": sr,
        "duration_s": round(len(x) / sr, 3),
        "n_harmonics": len(harmonics),
        "mean_blur_db": round(mean_blur, 3),
        "worst_blur_db": round(max(blurs), 3),
        "best_blur_db": round(min(blurs), 3),
        "max_blur_threshold_db": max_blur_db,
        "pass": (mean_blur <= max_blur_db) if max_blur_db is not None else None,
        "harmonics": harmonics,
    }
    return result

# ------------------------------------------- synthetic vowel + simulated freeze

def _formant_gain(f, f1, f2, f3):
    """Formant envelope at frequency f: three Lorentzian resonances."""
    def lorentz(fc, bw):
        return 1.0 / (1.0 + ((f - fc) / (bw / 2.0)) ** 2)
    return lorentz(f1, 80.0) + 0.6 * lorentz(f2, 120.0) + 0.35 * lorentz(f3, 160.0)


def synthesize_vowel(f0=DEFAULT_F0, duration=2.0, fs=48000,
                     vibrato_rate=0.0, vibrato_depth_semitones=0.0,
                     formants=VOWEL_A):
    """Synthesise a sustained vowel (harmonic series weighted by the
    formant envelope). vibrato_rate > 0 adds a vibrato of that rate in
    Hz and depth in semitones. Deterministic. This is a test signal,
    not a Vox8 render."""
    f1, f2, f3 = formants
    n = int(round(duration * fs))
    out = [0.0] * n
    phase = 0.0
    depth_ratio = 2.0 ** (vibrato_depth_semitones / 12.0) - 1.0
    for i in range(n):
        t = i / fs
        f0_t = f0
        if vibrato_rate > 0.0 and vibrato_depth_semitones > 0.0:
            f0_t = f0 * (1.0 + depth_ratio
                         * math.sin(2.0 * math.pi * vibrato_rate * t))
        phase += 2.0 * math.pi * f0_t / fs
        s = 0.0
        for h in range(1, 40):
            fh = h * f0_t
            if fh > fs / 2.0:
                break
            w = _formant_gain(fh, f1, f2, f3) / h
            s += w * math.sin(h * phase)
        out[i] = s
    peak = max(abs(v) for v in out) or 1.0
    return [v * 0.5 / peak for v in out]


def simulate_freeze(x, fs, fft_size=GHOST_FFT_SIZE, hop=GHOST_HOP,
                    frame_index=None, duration=1.0, mag_threshold_db=-80.0):
    """Simulate a spectral freeze: take one STFT frame of x (Hann,
    fft_size, hop) and resynthesise it as a bank of sinusoids at the
    bin frequencies, with the frozen frame's magnitudes and phases.
    This is what a phase-vocoder freeze does (hold the magnitude,
    advance the phase at each bin's frequency) -- the output keeps the
    original harmonic frequencies, it is NOT periodic at the frame
    rate. Bins more than mag_threshold_db below the strongest bin are
    dropped (they are numerical floor). Returns the frozen output.
    This is a stand-in for a Vox8 freeze render, for validating the
    blur measurement."""
    window = _hann(fft_size)
    frames = []
    for start in range(0, len(x) - fft_size + 1, hop):
        frames.append([x[start + i] * window[i] for i in range(fft_size)])
    if not frames:
        raise ValueError("signal too short for a freeze frame")
    if frame_index is None:
        frame_index = len(frames) // 2
    frame_index = max(0, min(len(frames) - 1, frame_index))
    spec = _fft([complex(v, 0.0) for v in frames[frame_index]])
    # Bins 0..fft_size/2, magnitude + phase. Drop the floor.
    mags = [abs(spec[k]) for k in range(fft_size // 2 + 1)]
    max_mag = max(mags) if mags else 0.0
    if max_mag <= 0.0:
        raise ValueError("freeze frame is silent")
    floor = max_mag * 10.0 ** (mag_threshold_db / 20.0)
    partials = []
    for k in range(fft_size // 2 + 1):
        if mags[k] < floor:
            continue
        f_k = k * fs / fft_size
        if f_k <= 0.0 or f_k >= fs / 2.0:
            continue
        phase = math.atan2(spec[k].imag, spec[k].real)
        partials.append((f_k, mags[k], phase))
    if not partials:
        raise ValueError("no partials above the %.0f dB floor"
                         % mag_threshold_db)
    n_out = int(round(duration * fs))
    out = [0.0] * n_out
    for f_k, amp, phase in partials:
        w = 2.0 * math.pi * f_k / fs
        for i in range(n_out):
            out[i] += amp * math.cos(w * i + phase)
    # Normalise to peak 0.5.
    peak = max(abs(v) for v in out) or 1.0
    return [v * 0.5 / peak for v in out]


# ------------------------------------------------------------------------ CLI

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Freeze-blur test: measure the spectral blur of a "
                    "frozen (or sustained) vibrato vowel, peak-bin vs "
                    "adjacent-bin energy per harmonic.")
    parser.add_argument("wav", nargs="?",
                        help="WAV of a frozen or sustained vowel")
    parser.add_argument("--f0", type=float, default=DEFAULT_F0,
                        help="vowel fundamental in Hz (default: 110)")
    parser.add_argument("--fft-size", type=int, default=DEFAULT_FFT_SIZE,
                        help="analysis FFT size (default: 4096)")
    parser.add_argument("--compare",
                        help="second WAV (e.g. corrected freeze) to compare "
                             "against the first; reports the blur difference")
    parser.add_argument("--max-blur-db", type=float, default=None,
                        help="pass threshold on the mean blur in dB (more "
                             "negative = sharper). Omit to report the value "
                             "only.")
    parser.add_argument("--generate-test", metavar="WAV",
                        help="generate the validation set (static vowel, "
                             "vibrato vowel, simulated freeze) and write the "
                             "vibrato vowel to WAV, then exit. The other two "
                             "are written next to it as *_static.wav and "
                             "*_frozen.wav")
    parser.add_argument("--duration", type=float, default=2.0,
                        help="duration in seconds for --generate-test "
                             "(default: 2.0)")
    parser.add_argument("--sample-rate", type=int, default=48000,
                        help="sample rate for --generate-test (default: 48000)")
    parser.add_argument("--out",
                        help="write the JSON result to this path (default: stdout)")
    args = parser.parse_args(argv)

    if args.generate_test:
        base = Path(args.generate_test)
        static = synthesize_vowel(f0=args.f0, duration=args.duration,
                                  fs=args.sample_rate)
        vibrato = synthesize_vowel(f0=args.f0, duration=args.duration,
                                   fs=args.sample_rate,
                                   vibrato_rate=VIBRATO_RATE,
                                   vibrato_depth_semitones=VIBRATO_DEPTH)
        frozen = simulate_freeze(vibrato, args.sample_rate,
                                 duration=1.0)
        static_path = base.with_name(base.stem + "_static" + base.suffix)
        frozen_path = base.with_name(base.stem + "_frozen" + base.suffix)
        write_wav(static_path, static, args.sample_rate)
        write_wav(base, vibrato, args.sample_rate)
        write_wav(frozen_path, frozen, args.sample_rate)
        print("generated %s (vibrato vowel, %.0f Hz, %.1f Hz vibrato, "
              "+/-%.1f semitone)" % (base, args.f0, VIBRATO_RATE, VIBRATO_DEPTH))
        print("generated %s (static vowel)" % static_path)
        print("generated %s (simulated freeze)" % frozen_path)
        return 0

    if not args.wav:
        parser.error("a vowel WAV is required (or --generate-test)")
    result = analyze_freeze_blur(args.wav, args.f0, args.fft_size,
                                 max_blur_db=args.max_blur_db)
    if args.compare:
        other = analyze_freeze_blur(args.compare, args.f0, args.fft_size)
        # Correction gain: how much lower (more negative) the blur is in
        # the first file than in the second. Positive = the first file
        # is sharper (less blur).
        result["comparison"] = {
            "other_input": str(args.compare),
            "other_mean_blur_db": other["mean_blur_db"],
            "other_worst_blur_db": other["worst_blur_db"],
            "mean_blur_difference_db": round(
                other["mean_blur_db"] - result["mean_blur_db"], 3),
            "worst_blur_difference_db": round(
                other["worst_blur_db"] - result["worst_blur_db"], 3),
        }
    text = json.dumps(result, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
        print(str(out_path))
    else:
        print(text)
    if result["pass"] is False:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
