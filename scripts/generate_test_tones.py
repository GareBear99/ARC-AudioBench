#!/usr/bin/env python3
"""Generate deterministic WAV test tones for ARC-AudioBench."""
from __future__ import annotations
import argparse, math, wave, struct
from pathlib import Path

SR = 48000
DURATION = 2.0
AMP = 0.5

def write_wav(path: Path, samples, sr: int = SR):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = b''.join(struct.pack('<h', max(-32768, min(32767, int(x * 32767)))) for x in samples)
        w.writeframes(frames)

def sine(freq: float, seconds: float, sr: int):
    n = int(seconds * sr)
    return [AMP * math.sin(2 * math.pi * freq * i / sr) for i in range(n)]

def silence(seconds: float, sr: int):
    return [0.0] * int(seconds * sr)

def impulse(seconds: float, sr: int):
    data = [0.0] * int(seconds * sr)
    if data: data[0] = 1.0
    return data

def sawtooth_naive(freq: float, seconds: float, sr: int):
    """Naive sawtooth: a phase ramp with a discontinuity. Aliases by design --
    every harmonic above Nyquist folds back as inharmonic content. This is
    the signal the alias test must FAIL on."""
    n = int(seconds * sr)
    return [AMP * (2.0 * ((freq * i / sr) % 1.0) - 1.0) for i in range(n)]

def sawtooth_bandlimited(freq: float, seconds: float, sr: int):
    """Band-limited sawtooth: additive synthesis, harmonics k*freq up to
    Nyquist only, amplitude 1/k (the sawtooth Fourier series), normalised
    to peak AMP. No energy above Nyquist, so nothing folds back. This is
    the signal the alias test must PASS on."""
    n = int(seconds * sr)
    max_harm = int((sr / 2) // freq)
    out = []
    for i in range(n):
        t = i / sr
        s = 0.0
        for k in range(1, max_harm + 1):
            s += math.sin(2 * math.pi * k * freq * t) / k
        out.append((2.0 / math.pi) * s)
    peak = max((abs(x) for x in out), default=0.0) or 1.0
    return [x * AMP / peak for x in out]

def sweep(start: float, end: float, seconds: float, sr: int):
    n = int(seconds * sr)
    out=[]
    phase=0.0
    for i in range(n):
        t=i/max(1,n-1)
        f=start * ((end/start) ** t)
        phase += 2*math.pi*f/sr
        out.append(AMP*math.sin(phase))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out', default='data/test_tones')
    args=ap.parse_args()
    out=Path(args.out)
    write_wav(out/'sine_1000hz.wav', sine(1000,DURATION,SR))
    write_wav(out/'sine_100hz.wav', sine(100,DURATION,SR))
    write_wav(out/'sine_10000hz.wav', sine(10000,DURATION,SR))
    write_wav(out/'silence.wav', silence(DURATION,SR))
    write_wav(out/'impulse.wav', impulse(DURATION,SR))
    write_wav(out/'log_sweep_20_20000hz.wav', sweep(20,20000,DURATION,SR))
    # Alias-test pair (Therum section 7). 997 Hz does not divide 48000
    # evenly, so folded aliases land at non-harmonic frequencies and the
    # alias test can see them. Naive must FAIL the alias test;
    # band-limited must PASS it.
    write_wav(out/'sawtooth_naive_997hz.wav', sawtooth_naive(997,DURATION,SR))
    write_wav(out/'sawtooth_bandlimited_997hz.wav', sawtooth_bandlimited(997,DURATION,SR))
    print(f'Generated test tones in {out}')
if __name__ == '__main__': main()
