#!/usr/bin/env python3
"""Filter-response / cramping test for ARC-AudioBench.

Measures a filter's frequency response from a rendered log-sine-sweep WAV
and compares it to the analogue prototype, reporting the cramping error.

The cramping baseline (FreeEQ8 paper, proven finding): a standard digital
biquad (RBJ, bilinear transform) loses -3.383 dB against its analogue
prototype at the geometric-mean frequency, sqrt(fc * sr/2). The SVF does
not decramp. A decramping method closes that gap toward 0 dB.

Method: the input is a log sine sweep (20 Hz to 20 kHz by default) rendered
through the filter under test, covering the whole WAV from t=0. The sweep
is split into 1/12-octave bins; the RMS in each bin gives the digital
magnitude at the bin's geometric-centre frequency. The analogue prototype
magnitude at the same frequency is computed from the standard analogue
transfer function (peaking / 2nd-order lowpass / 2nd-order highpass).
Error = digital - analogue, in dB. The headline number is the error at
the geometric-mean frequency f_geo = sqrt(fc * sr/2).

Pass: --max-error-db (default 1.0 dB) at f_geo. A standard RBJ biquad
measures about -3.4 dB there and FAILS this threshold -- correctly, it is
not decramped. A decramping method should measure near 0 dB and PASS.
The measured error is the result; the threshold is a bench value, not a
literature value.

Reference render: --render-reference renders the same sweep through a
built-in Python RBJ biquad (the same coefficients RBJ's Audio EQ
Cookbook gives) and writes the WAV, so the test can be validated against
a known filter. The analytical error for that biquad (from the z-transform
of the coefficients vs the analogue prototype) is computed alongside the
sweep measurement, and the two must agree.

Usage:
    python3 scripts/cramping_test.py render.wav --type peaking --fc 8000 \\
        --q 1.0 --gain-db 12 --out results/cramping/render.cramping.json
    python3 scripts/cramping_test.py --render-reference peaking --fc 8000 \\
        --q 1.0 --gain-db 12 --out data/test_tones/sweep_peaking_8000hz.wav
"""

import argparse
import json
import math
import struct
import sys
import wave
from pathlib import Path

SCHEMA_VERSION = "arc-audiobench-cramping-v1"

# The sweep the test expects, and the measurement grid.
SWEEP_F_START = 20.0
SWEEP_F_END = 20000.0
SWEEP_DURATION = 8.0          # seconds, reference render only
SWEEP_AMPLITUDE = 0.5
BINS_PER_OCTAVE = 12
SKIP_START = 0.2              # seconds skipped at the sweep start (filter transient)
SKIP_END = 0.1                # seconds skipped at the sweep end
DEFAULT_MAX_ERROR_DB = 1.0    # bench threshold at f_geo, not a literature value


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


# ------------------------------------------------------- RBJ biquad (reference)

def _rbj_common(fc, q, sr):
    w0 = 2.0 * math.pi * fc / sr
    alpha = math.sin(w0) / (2.0 * q)
    return w0, alpha


def rbj_peaking(fc, q, gain_db, sr):
    """RBJ peaking (bell) coefficients (b0,b1,b2,a1,a2), a0 normalised to 1."""
    w0, alpha = _rbj_common(fc, q, sr)
    a_gain = 10.0 ** (gain_db / 40.0)
    cos_w0 = math.cos(w0)
    a0 = 1.0 + alpha / a_gain
    b0 = (1.0 + alpha * a_gain) / a0
    b1 = (-2.0 * cos_w0) / a0
    b2 = (1.0 - alpha * a_gain) / a0
    a1 = (-2.0 * cos_w0) / a0
    a2 = (1.0 - alpha / a_gain) / a0
    return (b0, b1, b2), (a1, a2)


def rbj_lowpass(fc, q, sr):
    """RBJ 2nd-order lowpass coefficients (b0,b1,b2,a1,a2)."""
    w0, alpha = _rbj_common(fc, q, sr)
    cos_w0 = math.cos(w0)
    a0 = 1.0 + alpha
    b0 = ((1.0 - cos_w0) / 2.0) / a0
    b1 = (1.0 - cos_w0) / a0
    b2 = ((1.0 - cos_w0) / 2.0) / a0
    a1 = (-2.0 * cos_w0) / a0
    a2 = (1.0 - alpha) / a0
    return (b0, b1, b2), (a1, a2)


def rbj_highpass(fc, q, sr):
    """RBJ 2nd-order highpass coefficients (b0,b1,b2,a1,a2)."""
    w0, alpha = _rbj_common(fc, q, sr)
    cos_w0 = math.cos(w0)
    a0 = 1.0 + alpha
    b0 = ((1.0 + cos_w0) / 2.0) / a0
    b1 = (-(1.0 + cos_w0)) / a0
    b2 = ((1.0 + cos_w0) / 2.0) / a0
    a1 = (-2.0 * cos_w0) / a0
    a2 = (1.0 - alpha) / a0
    return (b0, b1, b2), (a1, a2)


def biquad_filter(b, a, x):
    """Direct Form II transposed biquad. b=(b0,b1,b2), a=(a1,a2)."""
    b0, b1, b2 = b
    a1, a2 = a
    z1 = 0.0
    z2 = 0.0
    y = []
    for sample in x:
        out = b0 * sample + z1
        z1 = b1 * sample - a1 * out + z2
        z2 = b2 * sample - a2 * out
        y.append(out)
    return y


def digital_magnitude_db(b, a, f, sr):
    """Analytical magnitude (dB) of the digital biquad at frequency f,
    from the z-transform evaluated on the unit circle."""
    b0, b1, b2 = b
    a1, a2 = a
    w = 2.0 * math.pi * f / sr
    cos_w = math.cos(w)
    cos_2w = math.cos(2.0 * w)
    sin_w = math.sin(w)
    sin_2w = math.sin(2.0 * w)
    # Numerator |b0 + b1 z^-1 + b2 z^-2|^2, denominator |1 + a1 z^-1 + a2 z^-2|^2.
    num_re = b0 + b1 * cos_w + b2 * cos_2w
    num_im = -(b1 * sin_w + b2 * sin_2w)
    den_re = 1.0 + a1 * cos_w + a2 * cos_2w
    den_im = -(a1 * sin_w + a2 * sin_2w)
    num = num_re * num_re + num_im * num_im
    den = den_re * den_re + den_im * den_im
    if num <= 0.0 or den <= 0.0:
        return float("-inf")
    return 10.0 * math.log10(num / den)


# ------------------------------------------------------- analogue prototype

def analogue_peaking_mag_db(f, fc, q, gain_db):
    """Analogue peaking (bell) magnitude in dB.

    H(s) = (s^2 + s*(A/Q)*w0 + w0^2) / (s^2 + s*(1/(A*Q))*w0 + w0^2),
    A = 10^(gain/40), w0 = 2*pi*fc. This is the prototype RBJ's peaking
    coefficients are the bilinear transform of."""
    a_gain = 10.0 ** (gain_db / 40.0)
    w = 2.0 * math.pi * f
    w0 = 2.0 * math.pi * fc
    w2 = w * w
    w02 = w0 * w0
    num = (w02 - w2) ** 2 + (w * (a_gain / q) * w0) ** 2
    den = (w02 - w2) ** 2 + (w * (1.0 / (a_gain * q)) * w0) ** 2
    return 10.0 * math.log10(num / den)


def analogue_lowpass_mag_db(f, fc, q):
    """Analogue 2nd-order lowpass magnitude in dB.

    H(s) = w0^2 / (s^2 + s*w0/Q + w0^2)."""
    w = 2.0 * math.pi * f
    w0 = 2.0 * math.pi * fc
    w2 = w * w
    w02 = w0 * w0
    den = (w02 - w2) ** 2 + (w * w0 / q) ** 2
    return 20.0 * math.log10(w02) - 10.0 * math.log10(den)


def analogue_highpass_mag_db(f, fc, q):
    """Analogue 2nd-order highpass magnitude in dB.

    H(s) = s^2 / (s^2 + s*w0/Q + w0^2)."""
    w = 2.0 * math.pi * f
    w0 = 2.0 * math.pi * fc
    w2 = w * w
    w02 = w0 * w0
    den = (w02 - w2) ** 2 + (w * w0 / q) ** 2
    return 20.0 * math.log10(w2) - 10.0 * math.log10(den)


def analogue_mag_db(filter_type, f, fc, q, gain_db):
    if filter_type == "peaking":
        return analogue_peaking_mag_db(f, fc, q, gain_db)
    if filter_type == "lowpass":
        return analogue_lowpass_mag_db(f, fc, q)
    if filter_type == "highpass":
        return analogue_highpass_mag_db(f, fc, q)
    raise ValueError("unknown filter type: %s" % filter_type)


# ------------------------------------------------------------- sweep render

def render_sweep(filter_type, fc, q, gain_db, sr, duration=SWEEP_DURATION,
                 f_start=SWEEP_F_START, f_end=SWEEP_F_END,
                 amplitude=SWEEP_AMPLITUDE):
    """Render a log sine sweep through the built-in RBJ biquad."""
    if filter_type == "peaking":
        b, a = rbj_peaking(fc, q, gain_db, sr)
    elif filter_type == "lowpass":
        b, a = rbj_lowpass(fc, q, sr)
    elif filter_type == "highpass":
        b, a = rbj_highpass(fc, q, sr)
    else:
        raise ValueError("unknown filter type: %s" % filter_type)
    n = int(round(duration * sr))
    phase = 0.0
    x = []
    for i in range(n):
        t = i / sr
        f = f_start * (f_end / f_start) ** (t / duration)
        phase += 2.0 * math.pi * f / sr
        x.append(amplitude * math.sin(phase))
    y = biquad_filter(b, a, x)
    return y, (b, a)


# ----------------------------------------------------------- response measure

def measure_response(samples, sr, f_start, f_end, input_amplitude,
                     reference=None):
    """Measure the digital magnitude response from a log sweep.

    Splits the sweep into 1/12-octave bins; the RMS in each bin gives the
    magnitude at the bin's geometric-centre frequency. Returns a list of
    (frequency_hz, magnitude_db). If `reference` (a WAV of the unfiltered
    sweep) is given, the input RMS per bin is measured from it instead of
    assuming `input_amplitude`."""
    duration = len(samples) / sr
    if duration <= SKIP_START + SKIP_END:
        raise ValueError("sweep too short (%.2f s) for the skip windows" % duration)
    n_octaves = math.log2(f_end / f_start)
    n_bins = int(round(n_octaves * BINS_PER_OCTAVE))
    results = []
    for i in range(n_bins):
        f_lo = f_start * 2.0 ** (i / BINS_PER_OCTAVE)
        f_hi = f_start * 2.0 ** ((i + 1) / BINS_PER_OCTAVE)
        f_c = math.sqrt(f_lo * f_hi)
        # Time window where the sweep is inside this bin. The sweep is
        # log-spaced in time: f(t) = f_start * (f_end/f_start)^(t/T).
        t_lo = duration * math.log2(f_lo / f_start) / math.log2(f_end / f_start)
        t_hi = duration * math.log2(f_hi / f_start) / math.log2(f_end / f_start)
        if t_hi <= SKIP_START or t_lo >= duration - SKIP_END:
            continue
        t_lo = max(t_lo, SKIP_START)
        t_hi = min(t_hi, duration - SKIP_END)
        i_lo = int(round(t_lo * sr))
        i_hi = int(round(t_hi * sr))
        if i_hi - i_lo < 16:
            continue
        seg = samples[i_lo:i_hi]
        rms = math.sqrt(sum(s * s for s in seg) / len(seg))
        if reference is not None:
            ref_seg = reference[i_lo:i_hi]
            ref_rms = math.sqrt(sum(s * s for s in ref_seg) / len(ref_seg))
            if ref_rms <= 0.0:
                continue
            mag_db = 20.0 * math.log10(rms / ref_rms)
        else:
            if input_amplitude <= 0.0 or rms <= 0.0:
                continue
            # Sine RMS is amplitude/sqrt(2); |H| = rms_out * sqrt(2) / A_in.
            mag_db = 20.0 * math.log10(rms * math.sqrt(2.0) / input_amplitude)
        results.append((f_c, mag_db))
    return results


# ------------------------------------------------------------------- analysis

def run_cramping(wav_path, filter_type, fc, q, gain_db, input_amplitude,
                 f_start, f_end, max_error_db, reference_path=None):
    samples, sr = read_wav(wav_path)
    if sr < 2 * f_end:
        raise ValueError(
            "sample rate %d Hz is below 2x the sweep end %.0f Hz" % (sr, f_end))
    reference = None
    if reference_path is not None:
        reference, ref_sr = read_wav(reference_path)
        if ref_sr != sr:
            raise ValueError("reference sample rate %d != %d" % (ref_sr, sr))
    measured = measure_response(samples, sr, f_start, f_end,
                                input_amplitude, reference=reference)
    if len(measured) < 8:
        raise ValueError("too few measurement bins (%d); is this a log sweep "
                         "from %.0f to %.0f Hz?" % (len(measured), f_start, f_end))
    f_geo = math.sqrt(fc * sr / 2.0)
    points = []
    for f_c, mag_db in measured:
        ana_db = analogue_mag_db(filter_type, f_c, fc, q, gain_db)
        points.append({
            "frequency_hz": round(f_c, 3),
            "digital_mag_db": round(mag_db, 3),
            "analogue_mag_db": round(ana_db, 3),
            "error_db": round(mag_db - ana_db, 3),
        })
    # Headline: the error at the geometric-mean frequency (nearest bin).
    geo_point = min(points, key=lambda p: abs(math.log2(p["frequency_hz"] / f_geo)))
    geo_error = geo_point["error_db"]
    max_abs_error = max(abs(p["error_db"]) for p in points)
    fc_point = min(points, key=lambda p: abs(math.log2(p["frequency_hz"] / fc)))
    result = {
        "schema_version": SCHEMA_VERSION,
        "tool": "ARC-AudioBench",
        "analysis_type": "cramping_test",
        "input": str(wav_path),
        "filter": {
            "type": filter_type,
            "fc_hz": fc,
            "q": q,
            "gain_db": gain_db if filter_type == "peaking" else None,
        },
        "sample_rate_hz": sr,
        "sweep": {"f_start_hz": f_start, "f_end_hz": f_end,
                  "duration_s": round(len(samples) / sr, 3),
                  "input_amplitude": input_amplitude,
                  "reference_wav": str(reference_path) if reference_path else None},
        "geometric_mean_hz": round(f_geo, 3),
        "error_at_geometric_mean_db": geo_error,
        "error_at_geometric_mean_frequency_hz": geo_point["frequency_hz"],
        "error_at_fc_db": fc_point["error_db"],
        "max_abs_error_db": round(max_abs_error, 3),
        "max_error_db_threshold": max_error_db,
        "pass": abs(geo_error) <= max_error_db,
        "points": points,
    }
    return result


# ------------------------------------------------------------------------ CLI

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Filter-response / cramping test: measure a filter's "
                    "response from a log-sweep WAV and compare it to the "
                    "analogue prototype.")
    parser.add_argument("wav", nargs="?",
                        help="WAV of a log sine sweep through the filter")
    parser.add_argument("--type", dest="filter_type", default="peaking",
                        choices=["peaking", "lowpass", "highpass"],
                        help="filter type (default: peaking)")
    parser.add_argument("--fc", type=float, default=8000.0,
                        help="filter centre/cutoff frequency in Hz (default: 8000)")
    parser.add_argument("--q", type=float, default=1.0,
                        help="filter Q (default: 1.0)")
    parser.add_argument("--gain-db", type=float, default=12.0,
                        help="peaking gain in dB (default: 12)")
    parser.add_argument("--input-amplitude", type=float, default=SWEEP_AMPLITUDE,
                        help="sweep input amplitude, peak (default: 0.5)")
    parser.add_argument("--reference",
                        help="WAV of the unfiltered sweep; input level is "
                             "measured per bin from it instead of assuming "
                             "--input-amplitude")
    parser.add_argument("--f-start", type=float, default=SWEEP_F_START,
                        help="sweep start frequency in Hz (default: 20)")
    parser.add_argument("--f-end", type=float, default=SWEEP_F_END,
                        help="sweep end frequency in Hz (default: 20000)")
    parser.add_argument("--sample-rate", type=int, default=48000,
                        help="sample rate for --render-reference (default: 48000)")
    parser.add_argument("--max-error-db", type=float, default=DEFAULT_MAX_ERROR_DB,
                        help="pass threshold on |error| at the geometric-mean "
                             "frequency in dB (default: 1.0)")
    parser.add_argument("--render-reference", metavar="WAV",
                        help="render the sweep through the built-in RBJ "
                             "biquad and write it to WAV, then exit")
    parser.add_argument("--out",
                        help="write the JSON result to this path (default: stdout)")
    args = parser.parse_args(argv)

    if args.render_reference:
        samples, (b, a) = render_sweep(
            args.filter_type, args.fc, args.q, args.gain_db,
            args.sample_rate)
        write_wav(args.render_reference, samples, args.sample_rate)
        # Analytical error at the geometric mean, for comparison with the
        # sweep measurement of the same render.
        f_geo = math.sqrt(args.fc * args.sample_rate / 2.0)
        ana = analogue_mag_db(args.filter_type, f_geo, args.fc, args.q,
                              args.gain_db)
        dig = digital_magnitude_db(b, a, f_geo, args.sample_rate)
        print("rendered %s (%s, fc=%.0f Hz, Q=%.2f, gain=%.1f dB, %d Hz, "
              "%.1f s)" % (args.render_reference, args.filter_type, args.fc,
                           args.q, args.gain_db, args.sample_rate,
                           SWEEP_DURATION))
        print("analytical error at geometric mean %.1f Hz: %.3f dB "
              "(digital %.3f dB, analogue %.3f dB)"
              % (f_geo, dig - ana, dig, ana))
        return 0

    if not args.wav:
        parser.error("a sweep WAV is required (or --render-reference)")
    result = run_cramping(
        args.wav, args.filter_type, args.fc, args.q, args.gain_db,
        args.input_amplitude, args.f_start, args.f_end,
        args.max_error_db, reference_path=args.reference)
    text = json.dumps(result, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
        print(str(out_path))
    else:
        print(text)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
