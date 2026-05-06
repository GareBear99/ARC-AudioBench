#!/usr/bin/env python3
"""Analyze WAV files and emit reproducible ARC-AudioBench JSON.

No third-party dependencies are required. 16/24/32-bit PCM input is supported.
"""
from __future__ import annotations
import argparse, json, math, wave, hashlib, struct, datetime
from pathlib import Path
from typing import List, Tuple

TOOL_VERSION = "1.0.0-rc1"

def _decode_pcm(raw: bytes, width: int) -> List[float]:
    if width == 1:
        return [((b - 128) / 128.0) for b in raw]
    if width == 2:
        vals = struct.unpack('<' + 'h' * (len(raw)//2), raw)
        return [v / 32768.0 for v in vals]
    if width == 3:
        out=[]
        for i in range(0, len(raw), 3):
            b = raw[i:i+3]
            if len(b) < 3: break
            val = int.from_bytes(b + (b'\xff' if b[2] & 0x80 else b'\x00'), 'little', signed=True)
            out.append(val / 8388608.0)
        return out
    if width == 4:
        vals = struct.unpack('<' + 'i' * (len(raw)//4), raw)
        return [v / 2147483648.0 for v in vals]
    raise ValueError(f'Unsupported PCM sample width: {width} bytes')

def read_wav(path: Path) -> Tuple[List[float], int, int, int, int]:
    with wave.open(str(path), 'rb') as w:
        channels = w.getnchannels()
        width = w.getsampwidth()
        sr = w.getframerate()
        nframes = w.getnframes()
        raw = w.readframes(nframes)
    vals = _decode_pcm(raw, width)
    if channels > 1:
        mono=[]
        for i in range(0, len(vals), channels):
            frame = vals[i:i+channels]
            if frame: mono.append(sum(frame)/len(frame))
        vals = mono
    return vals, sr, channels, width, nframes

def dominant_frequency(samples: List[float], sr: int) -> float:
    if len(samples) < 2 or sr <= 0:
        return 0.0
    crossings = 0
    prev = samples[0]
    for x in samples[1:]:
        if (prev <= 0 < x) or (prev >= 0 > x):
            crossings += 1
        prev = x
    duration = len(samples) / sr
    return (crossings / 2.0) / duration if duration else 0.0

def percentile_abs(samples: List[float], pct: float) -> float:
    if not samples: return 0.0
    arr = sorted(abs(x) for x in samples)
    idx = min(len(arr)-1, max(0, int(round((pct/100.0)*(len(arr)-1)))))
    return arr[idx]

def analyze(path: Path, label: str | None = None) -> dict:
    samples, sr, channels, width, nframes = read_wav(path)
    n = len(samples)
    peak = max((abs(x) for x in samples), default=0.0)
    rms = math.sqrt(sum(x*x for x in samples)/n) if n else 0.0
    mean = sum(samples)/n if n else 0.0
    clipping = sum(1 for x in samples if abs(x) >= 0.999)
    duration = nframes / sr if sr else 0.0
    crest = (peak / rms) if rms else 0.0
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    zero_samples = sum(1 for x in samples if abs(x) < 1e-12)
    return {
        'schema_version': 'arc-audiobench-result-v1',
        'tool': 'ARC-AudioBench',
        'tool_version': TOOL_VERSION,
        'analysis_type': 'wav_basic',
        'label': label or path.stem,
        'source_file': str(path),
        'sha256': sha,
        'created_utc': datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'sample_rate': sr,
        'channels': channels,
        'sample_width_bytes': width,
        'frames': nframes,
        'mono_analysis_frames': n,
        'duration_seconds': round(duration, 6),
        'peak': round(peak, 10),
        'rms': round(rms, 10),
        'crest_factor': round(crest, 10),
        'dc_offset': round(mean, 10),
        'clipping_samples': clipping,
        'zero_samples': zero_samples,
        'abs_p95': round(percentile_abs(samples, 95), 10),
        'abs_p99': round(percentile_abs(samples, 99), 10),
        'dominant_frequency_estimate_hz': round(dominant_frequency(samples, sr), 3),
        'pass': peak <= 1.0 and abs(mean) < 0.01 and clipping == 0,
    }

def main():
    ap = argparse.ArgumentParser(description='Analyze a WAV file and emit ARC-AudioBench JSON.')
    ap.add_argument('wav')
    ap.add_argument('--out')
    ap.add_argument('--label')
    args = ap.parse_args()
    result = analyze(Path(args.wav), label=args.label)
    txt = json.dumps(result, indent=2)
    if args.out:
        out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(txt, encoding='utf-8')
        print(out)
    else:
        print(txt)
if __name__ == '__main__': main()
