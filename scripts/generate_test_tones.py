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
    print(f'Generated test tones in {out}')
if __name__ == '__main__': main()
