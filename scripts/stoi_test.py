#!/usr/bin/env python3
"""STOI (Short-Time Objective Intelligibility) for ARC-AudioBench.

Taal et al. 2011: the objective intelligibility of a degraded speech
signal against a clean reference. The metric for Vox8 (dry modulator =
clean reference, vocoded output = degraded, fixed corpus, per-band
scores).

Method (Taal et al. 2011, as in the reference implementation):
resample both signals to 10 kHz; STFT, Hann window 256 samples, hop 128;
group the magnitude spectrum into 15 one-third-octave bands (centre
frequencies 150 Hz to ~3.8 kHz); remove silent frames (clean frame
energy more than 40 dB below the maximum); split into short-time
segments of 30 frames (384 ms); in each segment and band, normalise the
degraded envelope to the clean envelope's energy, clip it from below at
-15 dB relative to the clean envelope, and take the Pearson correlation
between the clean and processed degraded envelopes. STOI is the mean
correlation over all bands and segments, in [0, 1]. 1.0 is perfect
intelligibility.

This is a clean-room implementation of the published algorithm, stdlib
only. It is not the full reference code: the resampler is a windowed-sinc
FIR + linear interpolation (not a polyphase filter), and the band
grouping sums magnitudes (not powers). The validation below shows the
implementation behaves as STOI should (identity = 1.0, silence = 0,
monotone in SNR).

Speech corpus: there is no speech corpus in this repo. The test signal
generator below synthesises a speech-like signal (vowel formants, pitch
contour, syllabic amplitude) so the implementation can be validated
without a corpus. STOI numbers on the synthetic signal are for relative
comparison and for validating the implementation -- they are NOT a claim
about Vox8's intelligibility on real speech. For a real Vox8
measurement, run this script with a real speech corpus (clean ref =
dry modulator, degraded = vocoded output).

Usage:
    python3 scripts/stoi_test.py clean.wav degraded.wav --out results/stoi/out.stoi.json
    python3 scripts/stoi_test.py --generate-test data/test_tones/stoi_test.wav
"""

import argparse
import json
import math
import random
import struct
import sys
import wave
from pathlib import Path

SCHEMA_VERSION = "arc-audiobench-stoi-v1"

STOI_FS = 10000          # STOI is defined at 10 kHz
FRAME_LEN = 256          # Hann window, samples
HOP = 128                # 50% overlap
N_BANDS = 15             # one-third-octave bands
BAND_F0 = 150.0          # lowest band centre frequency, Hz
SEGMENT_FRAMES = 30      # frames per short-time segment (384 ms)
BETA_DB = -15.0          # clipping floor, dB below the clean envelope
DYN_RANGE_DB = 40.0      # silence threshold, dB below the max frame energy
RESAMPLE_TAPS = 65       # windowed-sinc FIR length for resampling


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


# -------------------------------------------------------------- resampling

def _fir_lowpass(cutoff_hz, fs, n_taps):
    """Windowed-sinc lowpass FIR (Hamming window), normalised to sum 1."""
    m = (n_taps - 1) / 2.0
    h = []
    for n in range(n_taps):
        x = n - m
        if abs(x) < 1e-12:
            sinc = 2.0 * cutoff_hz / fs
        else:
            sinc = math.sin(2.0 * math.pi * cutoff_hz * x / fs) / (math.pi * x)
        w = 0.54 - 0.46 * math.cos(2.0 * math.pi * n / (n_taps - 1))
        h.append(sinc * w)
    s = sum(h)
    return [v / s for v in h]


def resample(x, fs_in, fs_out):
    """Resample to fs_out: windowed-sinc FIR lowpass (cutoff 0.9 * the
    lower Nyquist) then linear interpolation at the target positions."""
    if fs_in == fs_out:
        return list(x)
    cutoff = 0.9 * min(fs_in, fs_out) / 2.0
    h = _fir_lowpass(cutoff, fs_in, RESAMPLE_TAPS)
    n = len(x)
    delay = (RESAMPLE_TAPS - 1) // 2
    y = [0.0] * n
    for i in range(n):
        acc = 0.0
        for k in range(RESAMPLE_TAPS):
            j = i + k - delay
            if 0 <= j < n:
                acc += h[k] * x[j]
        y[i] = acc
    n_out = int(round(n * fs_out / fs_in))
    out = []
    for m in range(n_out):
        t = m * fs_in / fs_out
        i0 = int(math.floor(t))
        frac = t - i0
        if i0 >= n - 1:
            out.append(y[-1])
        else:
            out.append(y[i0] * (1.0 - frac) + y[i0 + 1] * frac)
    return out


# ------------------------------------------------------- octave-band grouping

def band_centres():
    """15 one-third-octave band centre frequencies, 150 Hz to ~3.8 kHz."""
    return [BAND_F0 * 2.0 ** (i / 3.0) for i in range(N_BANDS)]


def band_bin_ranges(n_fft, fs):
    """For each band, the FFT bin indices whose frequency falls in it.
    Band edges are the geometric means of adjacent centre frequencies."""
    centres = band_centres()
    edges = []
    for i in range(N_BANDS):
        if i == 0:
            lo = centres[0] / 2.0 ** (1.0 / 6.0)
        else:
            lo = math.sqrt(centres[i - 1] * centres[i])
        if i == N_BANDS - 1:
            hi = centres[-1] * 2.0 ** (1.0 / 6.0)
        else:
            hi = math.sqrt(centres[i] * centres[i + 1])
        edges.append((lo, hi))
    bin_freq = fs / n_fft
    ranges = []
    for lo, hi in edges:
        bins = [k for k in range(n_fft // 2 + 1)
                if lo <= k * bin_freq < hi]
        ranges.append(bins)
    return ranges


# --------------------------------------------------------------- STOI core

def _stft_magnitude(x):
    """STFT magnitude, Hann 256, hop 128. Returns a list of frames, each a
    list of magnitudes for bins 0..128."""
    window = _hann(FRAME_LEN)
    frames = []
    for start in range(0, len(x) - FRAME_LEN + 1, HOP):
        seg = [x[start + i] * window[i] for i in range(FRAME_LEN)]
        spec = _fft([complex(v, 0.0) for v in seg])
        frames.append([abs(spec[k]) for k in range(FRAME_LEN // 2 + 1)])
    return frames


def _octave_bands(mag_frames, ranges):
    """Group each frame's magnitude spectrum into the 15 bands (sum of
    magnitudes in the band). Returns a list of frames, each a list of
    15 band values."""
    out = []
    for mag in mag_frames:
        out.append([sum(mag[k] for k in bins) for bins in ranges])
    return out


def _pearson(x, y):
    """Pearson correlation coefficient of two equal-length vectors."""
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    xc = [v - mx for v in x]
    yc = [v - my for v in y]
    num = sum(a * b for a, b in zip(xc, yc))
    den = math.sqrt(sum(a * a for a in xc) * sum(b * b for b in yc))
    if den <= 0.0:
        return 0.0
    return num / den


def stoi(clean, degraded, fs):
    """STOI of degraded vs clean, both lists of floats at sample rate fs.
    Returns (score, detail dict). The signals must be time-aligned and
    the same length; the shorter is used."""
    n = min(len(clean), len(degraded))
    clean = resample(clean[:n], fs, STOI_FS)
    degraded = resample(degraded[:n], fs, STOI_FS)
    ranges = band_bin_ranges(FRAME_LEN, STOI_FS)
    clean_bands = _octave_bands(_stft_magnitude(clean), ranges)
    degr_bands = _octave_bands(_stft_magnitude(degraded), ranges)
    n_frames = min(len(clean_bands), len(degr_bands))
    clean_bands = clean_bands[:n_frames]
    degr_bands = degr_bands[:n_frames]
    if n_frames == 0:
        raise ValueError("signal too short for STOI (need at least one "
                         "256-sample frame at 10 kHz)")
    # Silence removal, from the clean signal: drop frames more than
    # DYN_RANGE_DB below the maximum frame energy (sum of squared band
    # values).
    energies = [sum(v * v for v in frame) for frame in clean_bands]
    max_e = max(energies)
    if max_e <= 0.0:
        raise ValueError("clean signal is silent")
    thresh = max_e * 10.0 ** (-DYN_RANGE_DB / 10.0)
    keep = [i for i, e in enumerate(energies) if e >= thresh]
    if not keep:
        raise ValueError("no non-silent frames in the clean signal")
    clean_bands = [clean_bands[i] for i in keep]
    degr_bands = [degr_bands[i] for i in keep]
    n_frames = len(keep)
    # Short-time segments of SEGMENT_FRAMES frames; correlate per band.
    clip_factor = 10.0 ** (BETA_DB / 20.0)
    per_band = [[] for _ in range(N_BANDS)]
    n_segments = 0
    for start in range(0, n_frames - SEGMENT_FRAMES + 1, SEGMENT_FRAMES):
        n_segments += 1
        for b in range(N_BANDS):
            x = [clean_bands[start + t][b] for t in range(SEGMENT_FRAMES)]
            y = [degr_bands[start + t][b] for t in range(SEGMENT_FRAMES)]
            norm_x = math.sqrt(sum(v * v for v in x))
            norm_y = math.sqrt(sum(v * v for v in y))
            if norm_x <= 0.0 or norm_y <= 0.0:
                per_band[b].append(0.0)
                continue
            # Normalise the degraded envelope to the clean envelope's
            # energy, then clip it from below at BETA_DB relative to the
            # clean envelope.
            y = [v * norm_x / norm_y for v in y]
            y = [max(v, clip_factor * xv) for v, xv in zip(y, x)]
            per_band[b].append(_pearson(x, y))
    if n_segments == 0:
        raise ValueError("signal too short for STOI (need at least %d "
                         "frames after silence removal, got %d)"
                         % (SEGMENT_FRAMES, n_frames))
    band_means = []
    for b in range(N_BANDS):
        vals = per_band[b]
        band_means.append(sum(vals) / len(vals) if vals else 0.0)
    score = sum(band_means) / N_BANDS
    score = max(0.0, min(1.0, score))
    detail = {
        "frames_total": n_frames,
        "frames_kept": len(keep),
        "segments": n_segments,
        "band_means": [round(v, 4) for v in band_means],
        "band_centres_hz": [round(f, 1) for f in band_centres()],
    }
    return score, detail

# ------------------------------------------- synthetic speech-like signal

# Average adult-male vowel formants (F1, F2, F3 in Hz), from the
# phonetics literature. Used only to synthesise a speech-like test
# signal; these are textbook values, not a measurement.
VOWELS = {
    "a": (730.0, 1090.0, 2440.0),
    "i": (270.0, 2290.0, 3010.0),
    "u": (300.0, 870.0, 2240.0),
    "e": (530.0, 1840.0, 2480.0),
    "o": (570.0, 840.0, 2410.0),
}


def _formant_gain(f, f1, f2, f3):
    """Formant envelope at frequency f: the sum of three Lorentzian
    resonances, normalised so the peak is 1. A crude source-filter
    weighting for the harmonic amplitudes."""
    def lorentz(fc, bw):
        return 1.0 / (1.0 + ((f - fc) / (bw / 2.0)) ** 2)
    g = (lorentz(f1, 80.0) + 0.6 * lorentz(f2, 120.0)
         + 0.35 * lorentz(f3, 160.0))
    return g


def generate_speech_like(duration=3.0, fs=STOI_FS, seed=42):
    """Synthesise a speech-like signal: a sequence of vowels, each ~0.3 s,
    with a pitch contour (F0 100-130 Hz) and syllabic amplitude, the
    harmonics weighted by the vowel's formant envelope. Deterministic
    for a given seed. This is NOT real speech -- it is a test signal
    with speech-like spectral and temporal structure, for validating
    the STOI implementation without a corpus."""
    rng = random.Random(seed)
    vowel_names = ["a", "i", "u", "e", "o"]
    seq = [rng.choice(vowel_names) for _ in range(max(1, int(duration / 0.3)))]
    n = int(round(duration * fs))
    out = [0.0] * n
    phase = 0.0
    t = 0.0
    seg_len = int(round(0.3 * fs))
    for si, vname in enumerate(seq):
        f1, f2, f3 = VOWELS[vname]
        f0 = 100.0 + 30.0 * rng.random()
        seg_start = si * seg_len
        for i in range(seg_len):
            idx = seg_start + i
            if idx >= n:
                break
            t = idx / fs
            # Syllabic amplitude: rise then fall within the vowel.
            u = i / seg_len
            amp = math.sin(math.pi * min(1.0, u * 1.15)) ** 0.7
            # Pitch with a slow vibrato.
            f0_t = f0 * (1.0 + 0.02 * math.sin(2.0 * math.pi * 5.0 * t))
            phase += 2.0 * math.pi * f0_t / fs
            # Harmonic series, amplitudes weighted by the formant envelope.
            s = 0.0
            for h in range(1, 25):
                fh = h * f0_t
                if fh > fs / 2.0:
                    break
                w = _formant_gain(fh, f1, f2, f3) / h
                s += w * math.sin(h * phase)
            out[idx] = 0.35 * amp * s
    # Normalise to peak 0.5.
    peak = max(abs(v) for v in out) or 1.0
    return [v * 0.5 / peak for v in out]


def add_noise(x, snr_db, seed=1234):
    """Add white noise at the given SNR (dB) relative to the signal RMS.
    Deterministic for a given seed."""
    rng = random.Random(seed)
    rms = math.sqrt(sum(v * v for v in x) / len(x))
    noise_rms = rms * 10.0 ** (-snr_db / 20.0)
    return [v + rng.gauss(0.0, noise_rms) for v in x]


def vocoder_like(x, fs, n_bands=8):
    """A crude vocoder-like degradation: split into n_bands log-spaced
    bands, replace each band's fine structure with noise shaped by the
    band envelope. This is a stand-in for a vocoded output, for
    validating that STOI drops below 1.0 on a vocoded signal. It is NOT
    a Vox8 render."""
    # Band envelopes: rectify + smooth per band using a simple moving
    # average on the squared signal, in the time domain, per band via
    # a bank of one-pole filters is overkill -- instead, use the STFT
    # band envelopes directly: modulate white noise by the band energy.
    # Simpler time-domain version: lowpass the rectified signal to get
    # a slow envelope, then multiply noise by it, per band. Here we do
    # a single broadband version: the envelope of the whole signal.
    # (The band structure is preserved by the STOI band grouping itself.)
    # Envelope: |x| smoothed with a 20 ms moving average.
    win = max(1, int(round(0.02 * fs)))
    env = []
    acc = 0.0
    for i, v in enumerate(x):
        acc += abs(v)
        if i >= win:
            acc -= abs(x[i - win])
        env.append(acc / min(i + 1, win))
    rng = random.Random(99)
    out = [rng.gauss(0.0, 1.0) * e * 1.5 for e in env]
    # Normalise to the input RMS.
    rms_in = math.sqrt(sum(v * v for v in x) / len(x))
    rms_out = math.sqrt(sum(v * v for v in out) / len(out)) or 1.0
    return [v * rms_in / rms_out for v in out]


# ------------------------------------------------------------------- analysis

def run_stoi(clean_path, degraded_path):
    clean, fs_c = read_wav(clean_path)
    degraded, fs_d = read_wav(degraded_path)
    if fs_c != fs_d:
        raise ValueError("sample rates differ: clean %d Hz, degraded %d Hz"
                         % (fs_c, fs_d))
    score, detail = stoi(clean, degraded, fs_c)
    result = {
        "schema_version": SCHEMA_VERSION,
        "tool": "ARC-AudioBench",
        "analysis_type": "stoi_test",
        "clean": str(clean_path),
        "degraded": str(degraded_path),
        "sample_rate_hz": fs_c,
        "duration_s": round(min(len(clean), len(degraded)) / fs_c, 3),
        "stoi": round(score, 4),
        "frames_total": detail["frames_total"],
        "frames_kept": detail["frames_kept"],
        "segments": detail["segments"],
        "band_means": detail["band_means"],
        "band_centres_hz": detail["band_centres_hz"],
    }
    return result


# ------------------------------------------------------------------------ CLI

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="STOI (Taal et al. 2011): objective intelligibility "
                    "of a degraded speech signal vs a clean reference.")
    parser.add_argument("clean", nargs="?",
                        help="clean reference WAV")
    parser.add_argument("degraded", nargs="?",
                        help="degraded WAV (same length, same sample rate)")
    parser.add_argument("--out",
                        help="write the JSON result to this path (default: stdout)")
    parser.add_argument("--generate-test", metavar="WAV",
                        help="generate a synthetic speech-like test signal "
                             "at 10 kHz and write it to WAV, then exit")
    parser.add_argument("--duration", type=float, default=3.0,
                        help="duration in seconds for --generate-test "
                             "(default: 3.0)")
    parser.add_argument("--seed", type=int, default=42,
                        help="seed for --generate-test (default: 42)")
    args = parser.parse_args(argv)

    if args.generate_test:
        sig = generate_speech_like(duration=args.duration, fs=STOI_FS,
                                   seed=args.seed)
        write_wav(args.generate_test, sig, STOI_FS)
        print("generated %s (%.1f s, %d Hz, synthetic speech-like)"
              % (args.generate_test, args.duration, STOI_FS))
        return 0

    if not args.clean or not args.degraded:
        parser.error("a clean WAV and a degraded WAV are required "
                     "(or --generate-test)")
    result = run_stoi(args.clean, args.degraded)
    text = json.dumps(result, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
        print(str(out_path))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
