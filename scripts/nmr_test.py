#!/usr/bin/env python3
"""NMR test for ARC-AudioBench (Therum paper section 7, headline test).

Noise-to-mask ratio: the V\xc3\xa4lim\xc3\xa4ki school's criterion for alias
audibility (V\xc3\xa4lim\xc3\xa4ki & Huovilainen 2007; V\xc3\xa4lim\xc3\xa4ki, Nam, Smith &
Abel 2010; Kahles, Esqueda & V\xc3\xa4lim\xc3\xa4ki 2019). Aliases are judged
against the auditory masking curve, not a bare dB number: an alias is
inaudible when it lies below the masking threshold produced by the
signal itself (simultaneous masking from the harmonics) and by the
absolute threshold of hearing.

Method
------
1. Take a steady-state window (skip the onset, 16384 samples, Hann
   window) and compute a radix-2 FFT -- the same window and FFT as
   ``alias_test.py``, so the two tests agree on the spectrum.
2. Find spectral peaks above a -80 dBFS floor and classify each as
   harmonic (within 2 FFT bins of k*f0) or alias, exactly as the alias
   test does.
3. Build the masking threshold curve from the harmonic peaks, which
   are tonal maskers by construction for a periodic oscillator:
     - Bark scale (Zwicker 1961):
       z(f) = 13*atan(0.00076*f) + 3.5*atan((f/7500)^2)
     - Spreading function (Schroeder, Atal & Hall 1979, as used in
       MPEG-1 Psychoacoustic Model 1, ISO/IEC 11172-3):
       SF(dz) = 15.81 + 7.5*(dz+0.474) - 17.5*sqrt(1+(dz+0.474)^2) dB
       where dz = z - z_masker, in Bark. A masker at level L (dB SPL)
       contributes L + SF(dz) to the masking threshold at Bark z.
     - Absolute threshold of hearing (Terhardt 1979), in dB SPL:
       ATH(f) = 3.64*(f/1000)^-0.8 - 6.5*exp(-0.6*((f/1000)-3.3)^2)
                + 0.001*(f/1000)^4
       The ATH is an absolute level, so it needs a playback reference:
       0 dBFS is taken as 96 dB SPL by default (configurable with
       --ref-spl). Above 20 kHz Terhardt's formula is an extrapolation
       (the quartic term dominates); the ATH there is capped at 120 dB
       SPL, a level above which the concept of a threshold is meaningless.
4. The masking threshold at each alias frequency is the power sum of
   all harmonic-masker contributions plus the ATH, in the linear
   domain, converted back to dB.
5. For each alias, NMR = alias level - masking threshold, in dB.
   Two NMRs are reported:
     - NMR (total): against the full masking threshold (simultaneous
       masking + ATH). This is the audibility verdict.
     - NMR (simultaneous only): against the masking threshold from
       the harmonics alone, ignoring the ATH. This is the informative
       number when the ATH dominates (e.g. an alias above 20 kHz,
       where the ATH extrapolation alone would mask it): it says
       whether the harmonics themselves mask the alias.
   Pass: worst NMR (total) <= 0 dB -- every alias lies below the
   masking curve.

What this is NOT
---------------
- It is not the full MPEG-1 Psychoacoustic Model 1: there is no
  tonality estimation (the harmonics are tonal maskers by
  construction, which is correct for a periodic oscillator, but a
  general signal would need the full tonal/noise classification),
  no 0.5-Bark grouping, and no temporal masking. It is the
  simultaneous-masking + ATH model for a harmonic signal, which is
  exactly the case the alias test measures.
- It is not an ABX listening test. The NMR predicts audibility from
  the masking model; the paper's ABX protocol is the listening
  confirmation (Therum paper section 8). If listeners cannot
  distinguish, the NMR target is met in practice.
- The pass threshold (0 dB) is the criterion itself (masked =
  inaudible), not a provisional bench value like the alias test's
  -60 dBFS / -40 dB. The reference level (--ref-spl) affects the
  ATH contribution only; the simultaneous-masking part is
  level-independent.

References
----------
- V. V\xc3\xa4lim\xc3\xa4ki and A. Huovilainen, "Antialiasing Oscillators in
  Subtractive Synthesis," IEEE Signal Process. Mag. 24(2):116-125, 2007.
  (Taxonomy; NMR as the auditory error measure.)
- V. V\xc3\xa4lim\xc3\xa4ki, J. Nam, J. O. Smith and J. S. Abel,
  "Alias-Suppressed Oscillators Based on Differentiated Polynomial
  Waveforms," IEEE Trans. Audio Speech Lang. Process. 18(4):786-, 2010.
- E. Kahles, F. Esqueda & V. V\xc3\xa4lim\xc3\xa4ki, "Oversampling for
  Nonlinear Waveshaping," JAES 67(6):440-449, 2019. (A-weighted
  noise-to-mask reporting per quality setting.)
- E. Zwicker, "Subdivision of the Audible Frequency Range into
  Critical Bands," J. Acoust. Soc. Am. 33:248, 1961. (Bark scale.)
- M. R. Schroeder, B. S. Atal and J. L. Hall, "Optimizing Digital
  Speech Coders by Exploiting Masking Properties of the Human Ear,"
  J. Acoust. Soc. Am. 66:1647-1652, 1979. (Spreading function.)
- E. Terhardt, "Calculating Virtual Pitch," Hearing Research 1:155-182,
  1979. (Absolute threshold of hearing.)
- ISO/IEC 11172-3 (MPEG-1 Audio), Psychoacoustic Model 1.
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
DEFAULT_REF_SPL = 96.0
ATH_CAP_DB_SPL = 120.0
DEFAULT_NMR_DB = 0.0


def _fft(x):
    """Iterative radix-2 Cooley-Tukey FFT. x is a list of complex, len power of 2.

    Same method as alias_test.py (kept self-contained here so the two
    scripts do not share a private helper).
    """
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
    """Convert an FFT bin magnitude to dBFS for a Hann-windowed real signal."""
    amp = 4.0 * mag / n
    if amp <= 0:
        return -math.inf
    return 20.0 * math.log10(amp)


def bark(f):
    """Critical band rate in Bark (Zwicker 1961). f in Hz."""
    return 13.0 * math.atan(0.00076 * f) + 3.5 * math.atan((f / 7500.0) ** 2)


def spreading_db(dz):
    """Masking spreading function in dB (Schroeder et al. 1979, MPEG-1 Model 1).

    dz is the Bark distance from the masker (z - z_masker). Positive dz
    is above the masker in frequency, negative below. The function is
    asymmetric: it falls off faster below the masker than above it.
    """
    x = dz + 0.474
    return 15.81 + 7.5 * x - 17.5 * math.sqrt(1.0 + x * x)


def ath_db_spl(f):
    """Absolute threshold of hearing in dB SPL (Terhardt 1979).

    Valid over roughly 20 Hz - 20 kHz. Above 20 kHz the quartic term
    dominates and the formula extrapolates steeply; the result is
    capped at ATH_CAP_DB_SPL, above which the concept of a threshold
    is meaningless (beyond the threshold of pain).
    """
    fk = f / 1000.0
    v = (3.64 * fk ** (-0.8)
         - 6.5 * math.exp(-0.6 * (fk - 3.3) ** 2)
         + 0.001 * fk ** 4)
    return min(v, ATH_CAP_DB_SPL)


def _db_to_power(db):
    return 10.0 ** (db / 10.0)


def _power_to_db(p):
    if p <= 0:
        return -math.inf
    return 10.0 * math.log10(p)


def analyze_nmr(path, f0, ref_spl=DEFAULT_REF_SPL,
                nmr_db=DEFAULT_NMR_DB, label=None):
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
    peaks = []
    for k in range(1, half - 1):
        if mags[k] > floor_mag and mags[k] >= mags[k - 1] and mags[k] >= mags[k + 1]:
            peaks.append((k * bin_hz, mags[k]))
    tol_hz = HARMONIC_TOL_BINS * bin_hz
    max_harm = int((sr / 2) // f0)
    harmonics = []  # (freq, mag, k)
    aliases = []    # (freq, mag)
    for freq, mag in peaks:
        k = round(freq / f0)
        if 1 <= k <= max_harm and abs(freq - k * f0) <= tol_hz:
            harmonics.append((freq, mag, k))
        else:
            aliases.append((freq, mag))
    # Tonal maskers: the harmonics, in dB SPL.
    maskers = []
    for freq, mag, k in harmonics:
        level_dbfs = _dbfs_from_fft_mag(mag, FFT_SIZE)
        maskers.append((freq, level_dbfs + ref_spl))
    def masking_threshold_db_spl(freq, include_ath=True):
        """Masking threshold at freq (dB SPL): power sum of the
        harmonic-masker spreading contributions plus the ATH."""
        total = 0.0
        z = bark(freq)
        for m_freq, m_spl in maskers:
            contrib = m_spl + spreading_db(z - bark(m_freq))
            total += _db_to_power(contrib)
        if include_ath:
            total += _db_to_power(ath_db_spl(freq))
        return _power_to_db(total)
    alias_rows = []
    for freq, mag in sorted(aliases, key=lambda a: -a[1]):
        level_dbfs = _dbfs_from_fft_mag(mag, FFT_SIZE)
        level_spl = level_dbfs + ref_spl
        thr_total = masking_threshold_db_spl(freq, include_ath=True)
        thr_simul = masking_threshold_db_spl(freq, include_ath=False)
        ath = ath_db_spl(freq)
        alias_rows.append({
            'frequency_hz': round(freq, 3),
            'level_dbfs': round(level_dbfs, 3),
            'masking_threshold_db_spl': round(thr_total, 3),
            'masking_threshold_simultaneous_db_spl': round(thr_simul, 3),
            'ath_db_spl': round(ath, 3),
            'nmr_db': round(level_spl - thr_total, 3),
            'nmr_simultaneous_db': round(level_spl - thr_simul, 3),
        })
    worst = max(alias_rows, key=lambda r: r['nmr_db']) if alias_rows else None
    # The simultaneous-only NMR reported alongside the worst alias is
    # that alias's own simultaneous-only NMR (not the max over all
    # aliases): it says whether the worst alias is masked by the
    # harmonics or only by the absolute threshold. Reporting the max
    # simultaneous-only NMR over all aliases would pick a different,
    # irrelevant alias (e.g. a near-DC peak the ATH masks anyway).
    worst_simul = worst
    fund = min(harmonics, key=lambda h: abs(h[0] - f0)) if harmonics else None
    fund_dbfs = _dbfs_from_fft_mag(fund[1], FFT_SIZE) if fund else -math.inf
    passed = (worst is None) or (worst['nmr_db'] <= nmr_db)
    return {
        'schema_version': 'arc-audiobench-nmr-v1',
        'tool': 'ARC-AudioBench',
        'tool_version': TOOL_VERSION,
        'analysis_type': 'nmr_test',
        'label': label or Path(path).stem,
        'source_file': str(path),
        'fundamental_hz': f0,
        'sample_rate': sr,
        'channels': channels,
        'fft_size': FFT_SIZE,
        'window_seconds': round(FFT_SIZE / sr, 6),
        'skip_seconds': SKIP_SECONDS,
        'noise_floor_dbfs': NOISE_FLOOR_DBFS,
        'reference_spl_db': ref_spl,
        'reference_note': '0 dBFS taken as {} dB SPL; the ATH contribution depends on this, the simultaneous-masking part does not.'.format(ref_spl),
        'fundamental_dbfs': round(fund_dbfs, 3) if fund else None,
        'harmonic_peak_count': len(harmonics),
        'alias_peak_count': len(aliases),
        'worst_nmr_db': worst['nmr_db'] if worst else None,
        'worst_nmr_hz': worst['frequency_hz'] if worst else None,
        'worst_nmr_simultaneous_db': worst_simul['nmr_simultaneous_db'] if worst_simul else None,
        'worst_nmr_simultaneous_hz': worst_simul['frequency_hz'] if worst_simul else None,
        'nmr_threshold_db': nmr_db,
        # Sorted by NMR descending (most audible first): NMR is the
        # decision metric, so the reported list is ordered by it, not
        # by level. The worst alias is often a quiet low-frequency
        # folded harmonic, not the loudest alias.
        'aliases': sorted(alias_rows, key=lambda r: -r['nmr_db'])[:20],
        'pass': bool(passed),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
    }


def main():
    ap = argparse.ArgumentParser(description='NMR test: noise-to-mask ratio of alias products against the auditory masking curve (Therum paper section 7).')
    ap.add_argument('wav')
    ap.add_argument('--f0', type=float, required=True, help='Fundamental frequency in Hz (use one that does not divide the sample rate, e.g. 997).')
    ap.add_argument('--out')
    ap.add_argument('--label')
    ap.add_argument('--ref-spl', type=float, default=DEFAULT_REF_SPL,
                    help='dB SPL taken as 0 dBFS (default 96). Affects the ATH contribution only.')
    ap.add_argument('--nmr-db', type=float, default=DEFAULT_NMR_DB,
                    help='Pass threshold on the worst NMR in dB (default 0: every alias below the masking curve).')
    args = ap.parse_args()
    result = analyze_nmr(Path(args.wav), args.f0,
                         ref_spl=args.ref_spl, nmr_db=args.nmr_db,
                         label=args.label)
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
