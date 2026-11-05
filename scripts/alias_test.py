#!/usr/bin/env python3
"""Alias test for ARC-AudioBench (Therum paper section 7, headline test).

Given a rendered WAV of a periodic oscillator at a known fundamental f0,
measure the alias products: spectral energy that is NOT at an integer
multiple of f0. Aliases are the inharmonic components a wavetable / naive
oscillator folds back from above Nyquist.

Method
------
1. Take a steady-state window (skip the onset, 16384 samples, Hann window).
2. Radix-2 FFT (pure Python, stdlib only -- no third-party dependency).
3. Find spectral peaks above a noise floor.
4. Classify each peak as harmonic (within 2 FFT bins of k*f0) or alias.
5. Report the alias-to-signal ratio (alias energy / harmonic energy, dB),
   the worst alias level (dBFS) and frequency, and the alias count.

Why f0 must not divide the sample rate
---------------------------------------
If f0 divides sr/2 evenly (e.g. 1000 Hz at 48 kHz), every folded alias
lands exactly on a harmonic bin and is invisible to this test. Use a
fundamental such as 997 Hz, for which folded aliases land at non-harmonic
frequencies and are detectable. The bundled alias test tones use 997 Hz
for this reason (see generate_test_tones.py).

What this is NOT (yet)
----------------------
Therum section 7 specifies the alias test as a noise-to-mask ratio (NMR):
aliases below the auditory masking curve, not a bare dB number. This script
measures the alias energy and the worst alias level -- the raw quantities
an NMR is computed from. A masking-curve model (the NMR itself) is the
next step and is NOT implemented here; the pass thresholds below are
provisional bench values, not literature values. Do not cite the numbers
from this script as an NMR.

Thresholds (provisional, configurable via CLI):
  --worst-alias-db  default -60 dBFS  (strongest single alias component)
  --asr-db          default -40 dB    (alias energy vs harmonic energy)
"""
from __future__ import annotations
import argparse, json, math, datetime, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_wav import read_wav

TOOL_VERSION = "1.0.0-rc1"
FFT_SIZE = 16384
SKIP_SECONDS = 0.5
NOISE_FLOOR_DBFS = -80.0
HARMONIC_TOL_BINS = 2.0
DEFAULT_WORST_ALIAS_DB = -60.0
DEFAULT_ASR_DB = -40.0

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

def _dbfs_from_fft_mag(mag, n):
    """Convert an FFT bin magnitude to dBFS for a Hann-windowed real signal.

    A sine of amplitude A gives |X| ~= A * N / 4 at its peak bin
    (Hann coherent gain 0.5, single-sided spectrum), so A = 4 * |X| / N.
    """
    amp = 4.0 * mag / n
    if amp <= 0:
        return -math.inf
    return 20.0 * math.log10(amp)

def analyze_alias(path, f0, worst_alias_db=DEFAULT_WORST_ALIAS_DB,
                  asr_db=DEFAULT_ASR_DB, label=None):
    samples, sr, channels, width, nframes = read_wav(Path(path))
    n = len(samples)
    skip = int(SKIP_SECONDS * sr)
    if n - skip < FFT_SIZE:
        raise ValueError(
            f"need at least {SKIP_SECONDS}s + {FFT_SIZE} samples "
            f"({(skip + FFT_SIZE) / sr:.2f}s at {sr} Hz); file has {n / sr:.2f}s")
    window = samples[skip:skip + FFT_SIZE]
    win = _hann(FFT_SIZE)
    x = [complex(window[i] * win[i], 0.0) for i in range(FFT_SIZE)]
    spec = _fft(x)
    half = FFT_SIZE // 2
    mags = [abs(spec[k]) for k in range(half)]
    bin_hz = sr / FFT_SIZE
    floor_mag = 10.0 ** (NOISE_FLOOR_DBFS / 20.0) * FFT_SIZE / 4.0
    # Peak detection: local maxima above the noise floor.
    peaks = []
    for k in range(1, half - 1):
        if mags[k] > floor_mag and mags[k] >= mags[k - 1] and mags[k] >= mags[k + 1]:
            peaks.append((k * bin_hz, mags[k]))
    # Classify peaks as harmonic or alias.
    tol_hz = HARMONIC_TOL_BINS * bin_hz
    max_harm = int((sr / 2) // f0)
    harmonics = []
    aliases = []
    for freq, mag in peaks:
        k = round(freq / f0)
        if 1 <= k <= max_harm and abs(freq - k * f0) <= tol_hz:
            harmonics.append((freq, mag, k))
        else:
            aliases.append((freq, mag))
    harm_energy = sum(m * m for _, m, _ in harmonics)
    alias_energy = sum(m * m for _, m in aliases)
    asr = 10.0 * math.log10(alias_energy / harm_energy) if harm_energy > 0 and alias_energy > 0 else (-math.inf if alias_energy == 0 else math.inf)
    worst = max(aliases, key=lambda a: a[1]) if aliases else None
    worst_dbfs = _dbfs_from_fft_mag(worst[1], FFT_SIZE) if worst else -math.inf
    worst_hz = worst[0] if worst else 0.0
    # Fundamental level: the harmonic peak nearest f0.
    fund = min(harmonics, key=lambda h: abs(h[0] - f0)) if harmonics else None
    fund_dbfs = _dbfs_from_fft_mag(fund[1], FFT_SIZE) if fund else -math.inf
    passed = (worst_dbfs <= worst_alias_db) and (asr <= asr_db)
    return {
        'schema_version': 'arc-audiobench-alias-v1',
        'tool': 'ARC-AudioBench',
        'tool_version': TOOL_VERSION,
        'analysis_type': 'alias_test',
        'label': label or Path(path).stem,
        'source_file': str(path),
        'fundamental_hz': f0,
        'sample_rate': sr,
        'channels': channels,
        'fft_size': FFT_SIZE,
        'window_seconds': round(FFT_SIZE / sr, 6),
        'skip_seconds': SKIP_SECONDS,
        'noise_floor_dbfs': NOISE_FLOOR_DBFS,
        'fundamental_dbfs': round(fund_dbfs, 3) if fund else None,
        'harmonic_peak_count': len(harmonics),
        'alias_peak_count': len(aliases),
        'alias_to_signal_ratio_db': round(asr, 3) if asr not in (math.inf, -math.inf) else None,
        'worst_alias_dbfs': round(worst_dbfs, 3) if worst else None,
        'worst_alias_hz': round(worst_hz, 3) if worst else None,
        'worst_alias_threshold_dbfs': worst_alias_db,
        'asr_threshold_db': asr_db,
        'aliases': [
            {'frequency_hz': round(f, 3), 'level_dbfs': round(_dbfs_from_fft_mag(m, FFT_SIZE), 3)}
            for f, m in sorted(aliases, key=lambda a: -a[1])[:20]
        ],
        'pass': bool(passed),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
    }

def main():
    ap = argparse.ArgumentParser(description='Alias test: measure inharmonic alias products in a rendered oscillator WAV.')
    ap.add_argument('wav')
    ap.add_argument('--f0', type=float, required=True, help='Fundamental frequency in Hz (use one that does not divide the sample rate, e.g. 997).')
    ap.add_argument('--out')
    ap.add_argument('--label')
    ap.add_argument('--worst-alias-db', type=float, default=DEFAULT_WORST_ALIAS_DB)
    ap.add_argument('--asr-db', type=float, default=DEFAULT_ASR_DB)
    args = ap.parse_args()
    result = analyze_alias(Path(args.wav), args.f0,
                           worst_alias_db=args.worst_alias_db,
                           asr_db=args.asr_db, label=args.label)
    txt = json.dumps(result, indent=2)
    if args.out:
        out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(txt, encoding='utf-8')
        print(out)
    else:
        print(txt)
    if not result['pass']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
